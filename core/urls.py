from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("restaurantes/", views.restaurantes, name="restaurantes"),
    path("restaurantes/<int:pk>/", views.detalhes, name="detalhes"),
    path("restaurantes/<int:pk>/fachada.svg", views.fachada, name="fachada"),
    path("restaurantes/<int:pk>/avaliar/", views.avaliar, name="avaliar"),
    path("restaurantes/<int:pk>/obrigado/", views.obrigado, name="obrigado"),
    path("restaurantes/<int:pk>/preferencia/", views.preferencia, name="preferencia"),
    path("restaurantes/<int:pk>/confirmar/<str:codigo>/", views.confirmar, name="confirmar"),
    path("restaurantes/<int:pk>/responder/<str:codigo>/", views.responder, name="responder"),
    path("restaurantes/<int:pk>/reivindicar/", views.reivindicar, name="reivindicar"),
    path("restaurantes/<int:pk>/editar/", views.editar_dados, name="editar_dados"),
    path("restaurantes/<int:pk>/trazer-para-ca/", views.mover_demo, name="mover_demo"),
    path("favoritos/", views.favoritos, name="favoritos"),
    path("minhas-avaliacoes/", views.minhas_avaliacoes, name="avaliacoes"),
    path("minhas-avaliacoes/<int:pk>/excluir/", views.excluir_avaliacao, name="excluir_avaliacao"),
    path("minhas-avaliacoes/atendimento/<int:pk>/excluir/", views.excluir_atendimento, name="excluir_atendimento"),
    path("perfil/", views.perfil, name="perfil"),
    path("perfil/excluir-conta/", views.excluir_conta, name="excluir_conta"),
    path("denunciar/<str:tipo>/<int:pk>/", views.denunciar, name="denunciar"),
    path("anuncio/<int:pk>/", views.anuncio, name="anuncio"),
    path("mapa/", views.mapa, name="mapa"),
    path("sobre/", views.pagina("core/sobre.html"), name="sobre"),
    path("perguntas-frequentes/", views.pagina("core/faq.html"), name="faq"),
    path("configuracoes/", views.pagina("core/configuracoes.html"), name="configuracoes"),
    path("offline/", views.pagina("pwa/offline.html"), name="offline"),
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("sw.js", views.service_worker, name="sw"),
]
