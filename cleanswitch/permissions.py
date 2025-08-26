from rest_framework import permissions
from cleanswitch.Helpers import renderResponse

class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self,request,view):
        if hasattr(request.user,'role') and request.user.role=='super admin':
            return True
        return False
    
    def __call__(self,request):
        if not self.has_permission(request,None):
            return renderResponse(data='You are not authorized to access this page',message='You are not authorized to access this page',status=401)
        return None

class IsAdmin(permissions.BasePermission):
    def has_permission(self,request,view):
        if hasattr(request.user,'role') and (request.user.role=='admin' or request.user.role=='super admin'):
            return True
        return False
    
    def __call__(self,request):
        if not self.has_permission(request,None):
            return renderResponse(data='You are not authorized to access this page',message='You are not authorized to access this page',status=401)
        return None
    
class IsAdminOrManager(permissions.BasePermission):
    def has_permission(self,request,view):
        if hasattr(request.user,'role') and (request.user.role=='admin' or request.user.role=='manager' or request.user.role=='super admin'):
            return True
        return False
    
    def __call__(self,request):
        if not self.has_permission(request,None):
            return renderResponse(data='You are not authorized to access this page',message='You are not authorized to access this page',status=401)
        return None

class IsReceptionist(permissions.BasePermission):
    def has_permission(self,request,view):
        if hasattr(request.user,'role') and (request.user.role=='receptionist' or request.user.role=='admin' or request.user.role=='manager' or request.user.role=='super admin'):
            return True
        return False
    
    def __call__(self,request):
        if not self.has_permission(request,None):
            return renderResponse(data='You are not authorized to access this page',message='You are not authorized to access this page',status=401)
        return None
