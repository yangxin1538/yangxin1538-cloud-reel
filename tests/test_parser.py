from app.parser import parse_filename


def test_movie():
    p = parse_filename("流浪地球2 (2023).mkv")
    assert p.kind == "movie"
    assert p.title == "流浪地球2"
    assert p.year == "2023"


def test_tv():
    p = parse_filename("三体.S01E01.2023.mkv")
    assert p.kind == "tv"
    assert p.season == 1
    assert p.episode == 1
    assert "三体" in p.title
