from unittest.mock import Mock, patch

from github_client import raw_fetch_user_stars, REPO_STAR_THRESHOLD


@patch("github_client.requests.get")
def test_raw_fetch_user_stars_paginates_and_filters_by_star_threshold(mock_get):
    # First page: two repos, one below the star threshold
    first_page = [
        {
            "full_name": "owner/high-star-repo",
            "language": "Python",
            "description": "Popular repo",
            "html_url": "https://github.com/owner/high-star-repo",
            "stargazers_count": REPO_STAR_THRESHOLD + 5,
            "topics": ["python"],
        },
        {
            "full_name": "owner/low-star-repo",
            "language": "Python",
            "description": "Not so popular",
            "html_url": "https://github.com/owner/low-star-repo",
            "stargazers_count": REPO_STAR_THRESHOLD - 1,
            "topics": [],
        },
    ]

    # Second page: empty list to stop pagination
    second_page = []

    def side_effect(url, headers):
        response = Mock()
        response.status_code = 200
        if "page=1" in url:
            response.json.return_value = first_page
        else:
            response.json.return_value = second_page
        return response

    mock_get.side_effect = side_effect

    results = raw_fetch_user_stars("testuser", token="dummy")

    # Only the high-star repo should be included
    assert len(results) == 1
    repo = results[0]
    assert repo["full_name"] == "owner/high-star-repo"
    assert repo["stars"] == REPO_STAR_THRESHOLD + 5


@patch("github_client.requests.get")
def test_raw_fetch_user_stars_handles_api_error_gracefully(mock_get):
    response = Mock()
    response.status_code = 500
    response.text = "Internal Server Error"
    mock_get.return_value = response

    results = raw_fetch_user_stars("testuser")

    # On error, function should return an empty list without raising
    assert results == []


