"""
URL configuration for loginProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from tkinter.font import names

from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import TemplateView


from usuariosApp import views
from usuariosApp.views import SignUpView
from django.conf import settings
from django.conf.urls.static import static




urlpatterns = [
    path('admin/', admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),  
    path("", views.lista_productos, name="home"),
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("publicar/", views.publicar_producto, name='publicar_producto'),
    path('editar/<int:pk>/', views.editar_producto, name='editar_producto'),  
    path('eliminar/<int:pk>/', views.eliminar_producto, name='eliminar_producto'),
    path('producto/<int:producto_id>/', views.detalle_producto, name='detalle_producto'),
    path('verify-email/', views.VerifyEmailView.as_view(), name='verify_email'),
    path('destacar/<int:producto_id>/', views.destacar_producto, name='destacar_producto'),
    path('toggle-favorito/', views.toggle_favorito, name='toggle_favorito'),
    path('comentarios/eliminar/<int:comentario_id>/', views.eliminar_comentario, name='eliminar_comentario'),
    path('inbox/', views.inbox, name='inbox'),
    path('conversations/<int:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('start-conversation/<int:recipient_id>/', views.start_conversation, name='start_conversation'),
    path('conversations/<int:conversation_id>/messages/send/', views.send_message, name='send_message'),
    path('conversations/', views.conversations_list, name='conversations_list'),
    path('conversations/<int:conversation_id>/messages/', views.get_conversation_messages, name='get_conversation_messages'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('reportar/<int:producto_id>/', views.reportar_producto, name='reportar_producto'),
    path('reportes/', views.lista_reportes, name='lista_reportes'),
    path('reporte/eliminar/<int:reporte_id>/', views.eliminar_reporte, name='eliminar_reporte'),
    path('comentario/reportar/<int:comentario_id>/', views.reportar_comentario, name='reportar_comentario'),
    path('reportes/comentarios/', views.listar_reportes_comentarios, name='reportes_comentarios'),
    path('reporte/comentario/eliminar/<int:reporte_id>/', views.eliminar_reporte_comentario, name='eliminar_reporte_comentario'),
    path('delete-account/', views.DeleteAccountView.as_view(), name='delete_account'),
    path('conversaciones/<int:conversation_id>/ocultar/', views.ocultar_conversacion, name='ocultar_conversacion'),
    path('mensajes/reportar/<int:message_id>/', views.report_message, name='report_message'),
    path('reportes/mensajes/', views.lista_reportes_mensajes, name='lista_reportes_mensajes'),
    path('reportes/mensajes/eliminar/<int:reporte_id>/', views.eliminar_reporte_mensaje, name='eliminar_reporte_mensaje'),
    path('reportes/mensajes/resolver/<int:reporte_id>/', views.resolver_reporte_mensaje, name='resolver_reporte_mensaje'),
    path('api/mensajes-no-leidos/', views.contar_mensajes_no_leidos, name='contar_mensajes_no_leidos'),
    path('administracion/usuarios/', views.gestion_usuarios, name='gestion_usuarios'),
    path('administracion/usuarios/estado/<int:user_id>/', views.cambiar_estado_usuario, name='cambiar_estado_usuario'),
    path('administracion/usuarios/eliminar/<int:user_id>/', views.eliminar_usuario_definitivo, name='eliminar_usuario_definitivo'),
]



 

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
