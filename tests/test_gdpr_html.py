"""Tests for the human-readable GDPR export."""

import re

from actionkit_cli.gdpr_html import ref_key, render_html

USER = {
    "id": 7,
    "email": "a@b.eu",
    "first_name": "Tim",
    "last_name": "Testing",
    "country": "Germany",
    "token": ".7.secret",
    "rand_id": 686245333,
    "resource_uri": "/rest/v1/user/7/",
    "lang": "/rest/v1/language/106/",
    "actions": "/rest/v1/action/?user=7",
    "fields": {"preferred_currency": "EUR"},
    "phones": [],
    "groups": [{"name": "can speak de", "resource_uri": "/rest/v1/usergroup/12/"}],
}


def export(**sections):
    data = {"exported_at": "2026-10-01T12:00:00+00:00", "email": "a@b.eu"}
    data["user"] = USER
    data.update(sections)
    return data


def test_ref_key_normalises_typed_resources():
    assert ref_key("/rest/v1/donationpage/53/") == ("page", "53")
    assert ref_key("/rest/v1/unsubscribeaction/9/") == ("action", "9")
    assert ref_key("/rest/v1/list/1/") == ("list", "1")
    assert ref_key("/rest/v1/transaction/1/") == ("transaction", "1")
    assert ref_key("not a uri") is None


def test_header_names_the_person_and_export_date():
    html = render_html(export(), {})
    assert "Tim Testing" in html
    assert "a@b.eu" in html
    assert "2026-10-01" in html


def test_profile_shows_custom_fields_and_group_names():
    html = render_html(export(), {})
    assert "Preferred currency" in html
    assert "EUR" in html
    assert "can speak de" in html


def test_internal_identifiers_and_uris_are_hidden():
    html = render_html(export(), {})
    assert "/rest/v1/" not in html
    assert ".7.secret" not in html
    assert "686245333" not in html


def test_references_are_replaced_by_titles():
    actions = [
        {
            "id": 47,
            "created_at": "2024-01-02T03:04:05.123",
            "page": "/rest/v1/donationpage/53/",
            "type": "Donation",
            "ip_address": "192.0.2.1",
            "resource_uri": "/rest/v1/donationaction/47/",
        }
    ]
    html = render_html(export(actions=actions), {("page", "53"): "Save the bees"})
    assert "Save the bees" in html
    assert "2024-01-02 03:04" in html
    assert "192.0.2.1" in html


def test_values_are_escaped():
    user = dict(USER, first_name="<script>alert(1)</script>")
    html = render_html(dict(export(), user=user), {})
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_empty_sections_say_no_records():
    html = render_html(export(actions=[]), {})
    assert "Actions" in html
    assert "No records" in html


def test_unknown_sections_are_still_rendered():
    html = render_html(export(newthings=[{"favourite_colour": "teal"}]), {})
    assert "Newthings" in html
    assert "Favourite colour" in html
    assert "teal" in html


def test_is_self_contained():
    html = render_html(export(), {})
    assert html.startswith("<!doctype html>")
    assert "<script" not in html
    assert not re.search(r"""(src|href)\s*=""", html)
    assert "@import" not in html


def test_columns_sharing_a_label_are_merged():
    recurring = [{"action": "/rest/v1/donationaction/3/", "order": "/rest/v1/order/8/"}]
    labels = {("action", "3"): "Save the bees", ("order", "8"): "Save the bees"}
    html = render_html(export(orderrecurrings=recurring), labels)
    table = html.split("<h2>Recurring donations</h2>")[1]
    assert table.count("<th>Campaign</th>") == 1
    assert table.count("Save the bees") == 1


def test_letters_section_shows_template_comment_and_recipients():
    action = {
        "created_at": "2024-04-22T08:40:00",
        "page": "/rest/v1/letterpage/6/",
        "resource_uri": "/rest/v1/letteraction/4/",
        "fields": {"comment": "Please <b>act</b>"},
        "targeted": ["/rest/v1/target/9/"],
    }
    labels = {("page", "6"): "Write to your MEP", ("target", "9"): "MEP Jane Doe"}
    letters = {("page", "6"): "Dear MEP,\n\nVote yes."}
    html = render_html(export(actions=[action]), labels, letters)
    section = html.split("<h2>Letters</h2>")[1].split("</section>")[0]
    assert "Write to your MEP" in section
    assert "MEP Jane Doe" in section
    assert "Dear MEP,\n\nVote yes." in section
    assert "Please &lt;b&gt;act&lt;/b&gt;" in section


def test_no_letters_section_without_letter_actions():
    assert "<h2>Letters</h2>" not in render_html(export(actions=[]), {})


def test_long_values_and_fields_go_in_a_full_width_row_below_the_record():
    actions = [
        {
            "created_at": "2024-01-02T03:04:05",
            "type": "Petition",
            "fields": {"comment": "I care about this " * 10, "utm_source": "x"},
            "targeted": [f"/rest/v1/target/{i}/" for i in range(10)],
        },
        {"created_at": "2024-02-02T03:04:05", "type": "Petition"},
    ]
    labels = {("target", str(i)): f"MEP Jane Doe {i}" for i in range(10)}
    table = render_html(export(actions=actions), labels).split("<h2>Actions</h2>")[1]
    table = table.split("</section>")[0]
    head = table.split("</thead>")[0]
    assert "<th>Fields</th>" not in head
    assert "<th>Recipients</th>" not in head
    assert "<th>Type</th>" in head
    detail = re.findall(r'<tr class="detail">(.*?)</tr>', table)
    assert len(detail) == 1
    assert "colspan=" in detail[0]
    assert "Comment" in detail[0] and "I care about this" in detail[0]
    assert "Utm source" in detail[0]
    assert "MEP Jane Doe 9" in detail[0]
    assert "<td>Petition</td>" in table


def test_profile_shows_user_id():
    html = render_html(export(), {})
    assert "<dt>User ID</dt><dd>7</dd>" in html


def test_actions_table_shows_action_and_page_ids():
    actions = [
        {"id": 47, "page": "/rest/v1/donationpage/53/", "type": "Donation"},
        {"id": 48, "page": "/rest/v1/petitionpage/99/", "type": "Petition"},
    ]
    html = render_html(export(actions=actions), {("page", "53"): "Save the bees"})
    table = html.split("<h2>Actions</h2>")[1].split("</section>")[0]
    head = re.findall(r"<th>(.*?)</th>", table)
    assert head[:3] == ["Action ID", "Campaign", "Page ID"]
    rows = re.findall(r"<tr>(.*?)</tr>", table)[1:]
    assert re.findall(r"<td>(.*?)</td>", rows[0])[:3] == ["47", "Save the bees", "53"]
    # The page ID still identifies a page whose title could not be found.
    assert re.findall(r"<td>(.*?)</td>", rows[1])[:3] == ["48", "", "99"]


def test_letters_show_action_and_page_ids():
    action = {
        "id": 4,
        "page": "/rest/v1/letterpage/6/",
        "resource_uri": "/rest/v1/letteraction/4/",
        "targeted": ["/rest/v1/target/9/"],
    }
    html = render_html(export(actions=[action]), {}, {("page", "6"): "Dear MEP,"})
    section = html.split("<h2>Letters</h2>")[1].split("</section>")[0]
    assert "<dt>Action ID</dt><dd>4</dd>" in section
    assert "<dt>Page ID</dt><dd>6</dd>" in section
