import unittest
from scripts.update import transform, version_key

def app(name, bid, version="1.0", date="2026-01-01"):
    return {"name":name,"bundleIdentifier":bid,"developerName":"Test","iconURL":"https://example.com/icon.png","localizedDescription":"Test","versions":[{"version":version,"date":date,"downloadURL":"https://example.com/app.ipa","size":100}]}

class UpdateTests(unittest.TestCase):
    def source(self, apps):
        return {"apiVersion":"v2","name":"Test","apps":apps}
    def test_no_duplicates(self):
        out, removed = transform(self.source([app("A","a"),app("B","b")]),{})
        self.assertEqual(len(out["apps"]),2)
        self.assertFalse(removed)
    def test_newer_version(self):
        out, _ = transform(self.source([app("Old","a","1.0"),app("New","a","2.0")]),{})
        self.assertEqual(out["apps"][0]["name"],"New")
    def test_newer_date(self):
        out, _ = transform(self.source([app("Old","a",date="2026-01-01"),app("New","a",date="2026-02-01")]),{})
        self.assertEqual(out["apps"][0]["name"],"New")
    def test_preferred_name(self):
        out, _ = transform(self.source([app("Old","a","1.0"),app("New","a","2.0")]),{"preferred_names":{"a":"Old"}})
        self.assertEqual(out["apps"][0]["name"],"Old")
    def test_missing_field(self):
        a=app("A","a")
        del a["iconURL"]
        with self.assertRaises(ValueError): transform(self.source([a]),{})
    def test_invalid_date(self):
        with self.assertRaises(ValueError): transform(self.source([app("A","a",date="bad")]),{})
    def test_invalid_url(self):
        a=app("A","a")
        a["versions"][0]["downloadURL"]="http://example.com/file"
        with self.assertRaises(ValueError): transform(self.source([a]),{})
    def test_empty_source(self):
        with self.assertRaises(ValueError): transform(self.source([]),{})
    def test_version_order(self):
        self.assertGreater(version_key("10.2"),version_key("9.9"))
    def test_unique_bundle_ids(self):
        out, _ = transform(self.source([app("A","a"),app("B","a"),app("C","b")]),{})
        self.assertEqual(len({x["bundleIdentifier"] for x in out["apps"]}),2)

if __name__ == "__main__":
    unittest.main()
