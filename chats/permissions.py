from rest_framework.permissions import IsAuthenticated


class IsAdmin():
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.profile.admin

class IsAdminOrReadAuthenticated(IsAuthenticated):
    def has_permission(self, request, view):
        if request.method == 'GET':
            return super().has_permission(request, view)
        return request.user.profile.admin