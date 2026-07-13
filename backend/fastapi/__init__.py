import re, inspect
class HTTPException(Exception):
    def __init__(self, status_code:int, detail:str=""):
        self.status_code=status_code; self.detail=detail
class Response:
    def __init__(self, content="", media_type="text/plain"):
        self.content=content; self.media_type=media_type
class APIRouter:
    def __init__(self, prefix=""):
        self.prefix=prefix; self.routes=[]
    def _add(self, method, path, fn): self.routes.append((method,self.prefix+path,fn)); return fn
    def get(self,path, **kw): return lambda fn: self._add("GET",path,fn)
    def post(self,path, **kw): return lambda fn: self._add("POST",path,fn)
class FastAPI:
    def __init__(self, title=""):
        self.title=title; self.routes=[]
    def include_router(self, router): self.routes.extend(router.routes)
    def handle(self, method, path, body):
        from fastapi.testclient import TestResponse
        for m,pat,fn in self.routes:
            if m!=method: continue
            names=re.findall(r"{(.*?)}", pat)
            rx='^'+re.sub(r"{.*?}", r"([^/]+)", pat)+'$'
            mt=re.match(rx,path)
            if not mt: continue
            kwargs=dict(zip(names,mt.groups()))
            try:
                sig=inspect.signature(fn)
                for name,param in sig.parameters.items():
                    if name not in kwargs:
                        ann=param.annotation
                        if body is not None and hasattr(ann,'__annotations__'):
                            kwargs[name]=ann(**body)
                result=fn(**kwargs)
                if isinstance(result, Response): return TestResponse(200, text=result.content, media_type=result.media_type)
                return TestResponse(200, data=result)
            except HTTPException as e:
                return TestResponse(e.status_code, data={"detail":e.detail})
        return TestResponse(404, data={"detail":"not found"})
