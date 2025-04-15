from django.contrib import admin


from .models import City,Polygon,DailyDistribution,DailyWorkForce,Summary,RouteSolution,Depot


admin.site.register(City)
admin.site.register(Depot)
admin.site.register(Polygon)
admin.site.register(DailyDistribution)
admin.site.register(DailyWorkForce)
admin.site.register(Summary)
admin.site.register(RouteSolution)