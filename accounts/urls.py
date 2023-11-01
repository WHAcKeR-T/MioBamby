from django.urls import path
from . import views
urlpatterns = [
    path('', views.home),
    path('orders/', views.orders),
    path('products/', views.products),
    path('update_status/', views.update_status, name='update_status'),
    path('create_article/', views.create_article, name='create_article'),
    path('delete_document/<str:ref>/', views.delete_document, name='delete_document'),
    path('edit_article/<str:ref>/', views.edit_article, name='edit_article'),
    path('generate_invoice/<str:order_ref>/', views.generate_invoice, name='generate_invoice'),
    path('network/', views.network, name='network'),
    path('search_orders/', views.search_orders, name='search_orders'),
    path('delete_order/<str:ref>/', views.delete_order, name='delete_order'),
    path('search_article/', views.search_article, name='search_article'),
    path('delete_Aff/<str:id>/', views.delete_Aff, name='delete_Aff'),
    path('mlm/', views.mlm_tree),

]
