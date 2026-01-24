from datetime import date

import pytest


def test_get_download_url_format():
    """Test download URL format."""
    from app.external.cooltrader import CoolTraderDownloader

    with pytest.MonkeyPatch().context() as m:
        m.setenv("COOLTRADER_USERNAME", "test_user")
        m.setenv("COOLTRADER_PASSWORD", "test_pass")

        downloader = CoolTraderDownloader()

    url = downloader._get_download_url(date(2024, 1, 15))
    assert url == "https://data.cooltrader.com.au/amember/eodfiles/nextday/csv/20240115.csv"


def test_get_download_url_various_dates():
    """Test URL generation for different dates."""
    from app.external.cooltrader import CoolTraderDownloader

    with pytest.MonkeyPatch().context() as m:
        m.setenv("COOLTRADER_USERNAME", "test_user")
        m.setenv("COOLTRADER_PASSWORD", "test_pass")

        downloader = CoolTraderDownloader()

    test_cases = [
        (date(2024, 1, 15), "20240115.csv"),
        (date(2024, 12, 31), "20241231.csv"),
        (date(2026, 1, 17), "20260117.csv"),
    ]

    for test_date, expected_filename in test_cases:
        url = downloader._get_download_url(test_date)
        assert (
            url
            == f"https://data.cooltrader.com.au/amember/eodfiles/nextday/csv/{expected_filename}"
        )


def test_date_string_format():
    """Test date to string conversion for CSV filename."""
    from datetime import date

    test_date = date(2024, 1, 15)
    date_str = test_date.strftime("%Y%m%d")
    assert date_str == "20240115"


def test_yesterday_date_calculation():
    """Test yesterday date calculation."""
    from datetime import date, timedelta

    today = date.today()
    yesterday = today - timedelta(days=1)

    assert (today - yesterday).days == 1


def test_csv_filename_format():
    """Test CSV filename follows YYYYMMDD.csv format."""
    filename = "20240115.csv"

    assert filename.endswith(".csv")
    assert len(filename) == 12  # YYYYMMDD.csv = 8 + 1 + 3
    assert filename[:4] == "2024"
    assert filename[4:6] == "01"
    assert filename[6:8] == "15"
