class TestResponse:
    def __init__(self, status_code, data=None, text=None, media_type="application/json"):
        self.status_code=status_code; self._data=data; self.text=text if text is not None else str(data); self.headers={"content-type":media_type}
    def json(self): return self._data

class TestClient:
    def __init__(self, app): self.app=app
    def get(self, path): return self.app.handle("GET", path, None)
    def post(self, path, json=None): return self.app.handle("POST", path, json)
