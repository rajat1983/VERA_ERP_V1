from utils.entitlements import feature_for_path, from_access


def test_feature_paths():
    assert feature_for_path("/pos") == "pos"
    assert feature_for_path("/pos/complete") == "pos"
    assert feature_for_path("/production/add") == "production"
    assert feature_for_path("/services/12/edit") == "services"
    assert feature_for_path("/settings") is None
    assert feature_for_path("/sales") is None


def test_from_access_defaults():
    ents = from_access({})
    assert ents["pos"] is True
    assert ents["max_users"] == 5
    locked = from_access({"allow_pos": 0, "allow_production": 1, "allow_services": 0, "max_users": 3})
    assert locked["pos"] is False
    assert locked["services"] is False
    assert locked["production"] is True
    assert locked["max_users"] == 3
