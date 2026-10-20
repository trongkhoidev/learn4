from app.modules.speaking.assessment.scoring import js_round, _clamp_band, overall_of

def test_js_round():
    assert js_round(6.25) == 6.0
    assert js_round(6.5) == 7.0
    assert js_round(6.75) == 7.0

def test_clamp_band():
    assert _clamp_band(6.25) == 6.5
    assert _clamp_band(6.75) == 7.0
    assert _clamp_band(6.1) == 6.0
    assert _clamp_band(8.9) == 9.0

def test_overall_of_with_zeros():
    # overall_of is now implemented as: math.floor((sum(xs) / len(xs)) * 2 + 0.5) / 2.0
    # Let's see how it behaves
    assert overall_of([0, 0, 7, 7]) == 3.5
    assert overall_of([6, 6, 7, 7]) == 6.5
    assert overall_of([6.5, 6.5, 6, 6]) == 6.5 # sum=25 / 4 = 6.25 -> half-up rounding -> 6.5
    assert overall_of([5, 5, 5, 5.5]) == 5.0 # sum=20.5 / 4 = 5.125 -> 5.0
    assert overall_of([7, 7, 7, 7.5]) == 7.0 # sum=28.5 / 4 = 7.125 -> 7.0
    assert overall_of([7, 7, 7.5, 7.5]) == 7.5 # sum=29 / 4 = 7.25 -> 7.5
