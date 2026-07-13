class BaseModel:
    def __init__(self, **kwargs):
        anns=getattr(self,'__annotations__',{})
        for k in anns: setattr(self,k,kwargs.get(k))
