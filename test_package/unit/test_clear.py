import mdfluence.__main__ as main_module
from mdfluence.api import MinimalConfluence as Confluence


def test_delete_subpages_empty_parent(mocker):
    """No children — nothing to delete."""
    confluence = mocker.Mock(spec=Confluence)
    confluence.get_child_pages.return_value = []

    main_module._delete_subpages(confluence, "parent-123")

    confluence.get_child_pages.assert_called_once_with("parent-123")
    confluence.delete_page.assert_not_called()


def test_delete_subpages_flat_children(mocker):
    """Deletes all direct children (no nesting)."""
    confluence = mocker.Mock(spec=Confluence)

    child1 = mocker.Mock()
    child1.id = "c1"
    child1.title = "Child 1"
    child2 = mocker.Mock()
    child2.id = "c2"
    child2.title = "Child 2"

    # First call returns children, recursive calls return empty
    confluence.get_child_pages.side_effect = [
        [child1, child2],  # children of parent
        [],  # children of c1
        [],  # children of c2
    ]

    main_module._delete_subpages(confluence, "parent-123")

    assert confluence.delete_page.call_count == 2
    confluence.delete_page.assert_any_call("c1")
    confluence.delete_page.assert_any_call("c2")


def test_delete_subpages_nested_children(mocker):
    """Recursively deletes nested children (depth-first)."""
    confluence = mocker.Mock(spec=Confluence)

    grandchild = mocker.Mock()
    grandchild.id = "gc1"
    grandchild.title = "Grandchild"
    child = mocker.Mock()
    child.id = "c1"
    child.title = "Child"

    confluence.get_child_pages.side_effect = [
        [child],  # children of parent
        [grandchild],  # children of c1
        [],  # children of gc1
    ]

    main_module._delete_subpages(confluence, "parent-123")

    assert confluence.delete_page.call_count == 2
    # Grandchild deleted before child (depth-first)
    calls = confluence.delete_page.call_args_list
    assert calls[0].args[0] == "gc1"
    assert calls[1].args[0] == "c1"


def test_delete_subpages_partial_failure(mocker):
    """Continues deleting remaining pages when one fails."""
    from requests import HTTPError

    confluence = mocker.Mock(spec=Confluence)

    child1 = mocker.Mock()
    child1.id = "c1"
    child1.title = "Child 1"
    child2 = mocker.Mock()
    child2.id = "c2"
    child2.title = "Child 2"

    confluence.get_child_pages.side_effect = [
        [child1, child2],
        [],
        [],
    ]

    response_mock = mocker.Mock()
    response_mock.content = b"permission denied"
    confluence.delete_page.side_effect = [
        HTTPError(response=response_mock),  # c1 fails
        None,  # c2 succeeds
    ]

    main_module._delete_subpages(confluence, "parent-123")

    assert confluence.delete_page.call_count == 2


def test_get_child_pages_pagination(requests_mock):
    """get_child_pages follows pagination links."""
    confluence = Confluence(host="http://example.com/api/", token="test")

    requests_mock.get(
        "http://example.com/api/content/123/child/page",
        json={
            "results": [{"id": "1", "title": "Page 1"}],
            "_links": {
                "next": "/api/content/123/child/page?start=1&limit=100",
            },
        },
    )
    requests_mock.get(
        "http://example.com/api/content/123/child/page?start=1&limit=100",
        json={
            "results": [{"id": "2", "title": "Page 2"}],
            "_links": {},
        },
    )

    results = confluence.get_child_pages("123")
    assert len(results) == 2
    assert results[0].title == "Page 1"
    assert results[1].title == "Page 2"


def test_get_child_pages_empty(requests_mock):
    """get_child_pages returns empty list for no children."""
    confluence = Confluence(host="http://example.com/api/", token="test")

    requests_mock.get(
        "http://example.com/api/content/123/child/page",
        json={"results": [], "_links": {}},
    )

    results = confluence.get_child_pages("123")
    assert results == []
