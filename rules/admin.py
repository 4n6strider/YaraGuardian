from django.contrib import admin

from .models import YaraTestFolder


class YaraTestFolderAdmin(admin.ModelAdmin):
    actions = ['delete_selected']
    list_display = ('name', 'path', 'description')


admin.site.register(YaraTestFolder, YaraTestFolderAdmin)
