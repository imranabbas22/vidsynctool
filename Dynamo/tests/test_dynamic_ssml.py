"""Tests for parse_dynamic_ssml function."""
import sys
sys.path.insert(0, 'E:\\auto-youtube-project\\app_build')

from dynamic_script import parse_dynamic_ssml


def test_three_scenes():
    ssml = 'Scene one text.<break time="600ms"/>Scene two text.<break time="600ms"/>Scene three text.'
    result = parse_dynamic_ssml(ssml, 3)
    assert len(result) == 3, f"Expected 3, got {len(result)}"
    assert "Scene one" in result[0]
    assert "Scene two" in result[1]
    assert "Scene three" in result[2]
    print(f"test_three_scenes PASS: {result}")


def test_five_scenes():
    parts = [f'Scene {i+1} text.' for i in range(5)]
    ssml = '<break time="600ms"/>'.join(parts)
    result = parse_dynamic_ssml(ssml, 5)
    assert len(result) == 5, f"Expected 5, got {len(result)}"
    for i in range(5):
        assert f'Scene {i+1}' in result[i]
    print(f"test_five_scenes PASS: {result}")


def test_one_scene_no_breaks():
    result = parse_dynamic_ssml('Just a single fact.', 1)
    assert len(result) == 1
    assert "Just a single fact" in result[0]
    print(f"test_one_scene_no_breaks PASS: {result}")


def test_padding():
    """When scene_count > actual segments, pad with empty strings."""
    ssml = 'First scene.<break time="600ms"/>Second scene.'
    result = parse_dynamic_ssml(ssml, 4)
    assert len(result) == 4, f"Expected 4, got {len(result)}"
    assert result[0] == "First scene."
    assert result[1] == "Second scene."
    assert result[2] == ""
    assert result[3] == ""
    print(f"test_padding PASS: {result}")


def test_wrapped_ssml():
    ssml = '<speak><voice name="en-US-AndrewNeural">Hello there.<break time="600ms"/>General Kenobi.</voice></speak>'
    result = parse_dynamic_ssml(ssml, 2)
    assert len(result) == 2
    assert "Hello there" in result[0]
    assert "General Kenobi" in result[1]
    print(f"test_wrapped_ssml PASS: {result}")


def test_eight_scenes():
    parts = [f'Scene {i+1} content.' for i in range(8)]
    ssml = '<break time="600ms"/>'.join(parts)
    result = parse_dynamic_ssml(ssml, 8)
    assert len(result) == 8
    for i in range(8):
        assert f'Scene {i+1}' in result[i]
    print(f"test_eight_scenes PASS")


def test_prosody_tags_preserved():
    """Prosody tags should be stripped when extracting plain text."""
    ssml = '<prosody pitch="-1.0st" rate="0.93">Hello there.</prosody><break time="600ms"/><prosody pitch="-1.0st" rate="0.93">General Kenobi.</prosody>'
    result = parse_dynamic_ssml(ssml, 2)
    assert len(result) == 2
    assert "Hello there" in result[0]
    assert "General Kenobi" in result[1]
    assert "<prosody" not in result[0]
    print(f"test_prosody_tags_preserved PASS: {result}")


if __name__ == "__main__":
    test_three_scenes()
    test_five_scenes()
    test_one_scene_no_breaks()
    test_padding()
    test_wrapped_ssml()
    test_eight_scenes()
    test_prosody_tags_preserved()
    print("\nAll parse_dynamic_ssml tests PASSED!")
