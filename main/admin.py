from django.contrib import admin

# Register your models here.
from .models import Post,Comment

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    # List View
    list_display = ('title', 'status', 'published_at', 'author')
    list_filter = ('status', 'published_at', 'author')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
    ordering = ('status', 'published_at')
    readonly_fields = ('created_at', 'updated_at')


    # Detail And Edit View
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'content', 'status', 'published_at', 'author','created_at', 'updated_at')
        }),
    )

    # Create View
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('title', 'slug', 'content', 'status', 'published_at', 'author')
        }),
    )


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'name', 'email', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'email', 'content')
    readonly_fields = ('created_at', 'updated_at')
