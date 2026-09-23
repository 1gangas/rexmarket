from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import CreateView
from rest_framework.reverse import reverse_lazy
from django.contrib.auth import login, authenticate
from usuariosApp.models import Producto, Favorito, Comentario, Message, Conversation, Reporte, ReporteComentario
from usuariosApp.forms import ProductoForm, ComentarioForm, CustomUserCreationForm 
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages
import uuid
from django.urls import reverse_lazy
from django.views import View
from django.utils.timezone import now, timedelta
from django.db.models import Avg, F, Q
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView
import re


# Create your views here.

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("verify_email")
    template_name = "registration/signup.html"

    def form_valid(self, form):
        # Guardar los datos del formulario en la sesión
        self.request.session['user_data'] = {
            'username': form.cleaned_data['username'],
            'password1': form.cleaned_data['password1'],
            'password2': form.cleaned_data['password2'],
            'email': form.cleaned_data['email'],
            'first_name': form.cleaned_data['first_name'],
            'last_name': form.cleaned_data['last_name'],
        }

        # Generar código de verificación
        verification_code = str(uuid.uuid4())[:6].strip()
        self.request.session['verification_code'] = verification_code.strip()

        # Enviar correo de verificación con el código
        send_mail(
            'Verifica tu correo - RexMarket',
            f'Hola {form.cleaned_data["first_name"]}, tu código de verificación es:{verification_code}\n\nPor favor ingresa este código para activar tu cuenta.',
            'rexmarket26@gmail.com',
            [form.cleaned_data['email']],
            fail_silently=False,
        )

        messages.success(self.request, 'Te hemos enviado un correo con el código de verificación.')
        return redirect(self.success_url)



@login_required
def publicar_producto(request):
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.vendedor = request.user
            producto.save()
            return redirect('home')
    else:
        form = ProductoForm()
    return render(request, 'publicar_producto.html', {'form': form})


def lista_productos(request):
    # Captura los parámetros de búsqueda y filtros
    query = request.GET.get('q', '').strip()
    categoria_seleccionada = request.GET.get('categoria', '')  # Captura la categoría seleccionada
    ordenar_por = request.GET.get('ordenar_por', '')  # Captura el orden seleccionado

    productos = Producto.objects.filter(activo=True).annotate(
        destacado_valido=Q(destacado_hasta__gte=now())
    ).order_by(
        F('destacado_hasta').desc(nulls_last=True)
    ).prefetch_related('favoritos')  # Prefetch de la relación favoritos para optimización

    # Filtrar por búsqueda
    if query:
        productos = productos.filter(
            Q(nombre__icontains=query) | Q(descripcion__icontains=query)
        )

    # Filtrar por categoría, favoritos o mis productos
    if categoria_seleccionada:
        if categoria_seleccionada == 'favoritos' and request.user.is_authenticated:
            productos = productos.filter(favoritos__usuario=request.user)
        elif categoria_seleccionada == 'mis_productos' and request.user.is_authenticated:
            productos = productos.filter(vendedor=request.user)
        else:
            productos = productos.filter(categoria=categoria_seleccionada)

    # Ordenar productos según la selección
    if ordenar_por == 'precio_asc':
        productos = productos.order_by('precio')
    elif ordenar_por == 'precio_desc':
        productos = productos.order_by('-precio')
    elif ordenar_por == 'valoracion':
        productos = productos.annotate(
            valoracion_promedio=Avg('comentarios__valoracion')
        ).order_by('-valoracion_promedio')

    # Calcular el promedio de valoraciones si no está ordenado por ello
    if ordenar_por != 'valoracion':
        for producto in productos:
            promedio = producto.comentarios.aggregate(promedio=Avg('valoracion'))['promedio']
            producto.valoracion_promedio = promedio if promedio is not None else 0

    # Paginación
    paginator = Paginator(productos, 21)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Determinar si los productos son favoritos del usuario autenticado
    if request.user.is_authenticated:
        favoritos_ids = set(request.user.favoritos.values_list('producto_id', flat=True))
        for producto in page_obj:
            producto.es_favorito_usuario = producto.id in favoritos_ids
    else:
        for producto in page_obj:
            producto.es_favorito_usuario = False

    # Agregar las opciones de filtros adicionales en las categorías
    categorias = list(Producto.CATEGORIAS) + [
        ('favoritos', 'Mis Favoritos'),
        ('mis_productos', 'Mis Productos')
    ]

    # Renderizar la plantilla con el contexto
    return render(request, 'index.html', {
        'page_obj': page_obj,
        'query': query,
        'categorias': categorias,
        'categoria_seleccionada': categoria_seleccionada,
        'ordenar_por': ordenar_por,
        'user': request.user
    })


def editar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)

    # Verificar si el usuario tiene permiso para editar
    if producto.vendedor != request.user and not request.user.is_superuser:
        return redirect('home')  # Redirigir si no es el dueño o no es superusuario

    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('home')  # Redirigir después de guardar
    else:
        form = ProductoForm(instance=producto)

    return render(request, 'editar_producto.html', {'form': form, 'producto': producto})

def eliminar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)

    # Verificar si el usuario tiene permiso para eliminar
    if producto.vendedor != request.user and not request.user.is_superuser:
        return redirect('home')

    # BORRADO LÓGICO: En lugar de usar producto.delete()
    producto.activo = False
    producto.save()
    
    return redirect('home')

def detalle_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    # Promedio de este producto específico
    promedio = producto.comentarios.aggregate(promedio=Avg('valoracion'))['promedio']
    producto.valoracion_promedio = promedio if promedio is not None else 0

    # NUEVO: Calcular la reputación global del vendedor (todos sus productos)
    reputacion = Comentario.objects.filter(producto__vendedor=producto.vendedor).aggregate(promedio=Avg('valoracion'))['promedio']
    reputacion_vendedor = reputacion if reputacion is not None else 0

    form_comentario = ComentarioForm()
    comentarios = producto.comentarios.all()

    if request.method == 'POST' and 'comentario' in request.POST:
        if request.user.is_authenticated:
            form_comentario = ComentarioForm(request.POST)
            if form_comentario.is_valid():
                comentario = form_comentario.save(commit=False)
                comentario.usuario = request.user
                comentario.producto = producto
                comentario.save()
                messages.success(request, "Comentario añadido exitosamente")
                return redirect('detalle_producto', producto_id=producto.id)
        else:
            messages.error(request, "Debes iniciar sesión para dejar un comentario")

    context = {
        'producto': producto,
        'form_comentario': form_comentario,
        'comentarios': comentarios,
        'reputacion_vendedor': reputacion_vendedor, 
    }

    return render(request, 'detalle_producto.html', context)

def login_register_view(request):
    login_form = AuthenticationForm()
    register_form = UserCreationForm()

    if request.method == "POST":
        if "login_submit" in request.POST:  # Formulario de inicio de sesión
            login_form = AuthenticationForm(data=request.POST)
            if login_form.is_valid():
                user = login_form.get_user()
                login(request, user)
                return redirect('home')  # Redirecciona al inicio
        elif "register_submit" in request.POST:  # Formulario de registro
            register_form = UserCreationForm(request.POST)
            if register_form.is_valid():
                register_form.save()
                user = authenticate(
                    username=register_form.cleaned_data['username'],
                    password=register_form.cleaned_data['password1']
                )
                if user:
                    login(request, user)
                    return redirect('home')

    return render(request, 'registration/login.html', {
        'login_form': login_form,
        'register_form': register_form
    })

class VerifyEmailView(View):
    def get(self, request):
        return render(request, 'registration/verify_email.html')

    def post(self, request):
        verification_code = request.POST.get('verification_code')
        session_code = request.session.get('verification_code')

        if verification_code == session_code:
            user_data = request.session.get('user_data')

            # Crear el usuario después de verificar el código
            user = User.objects.create_user(
                username=user_data['username'],
                password=user_data['password1'],
                email=user_data['email'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name']
            )
            user.is_active = True  # Activar el usuario
            user.save()

            # Limpiar la sesión
            del request.session['user_data']
            del request.session['verification_code']

            messages.success(request, '¡Cuenta creada exitosamente! Ahora puedes iniciar sesión')
            return redirect('login')

        messages.error(request, 'El código de verificación no es válido. Intenta de nuevo.')
        return redirect('verify_email')
    
@login_required
def destacar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id, vendedor=request.user)
    
    if request.method == 'POST':
        duracion = request.POST.get('duracion')  # 1, 7 o 14 días
        precios = {
            '1': 490,
            '7': 2990,
            '14': 4990
        }

        if duracion in precios:
            # Actualizar fecha de destacación
            dias = int(duracion)
            producto.destacado_hasta = now() + timedelta(days=dias)
            producto.save()
            messages.success(request, f'El producto {producto.nombre} ha sido destacado por {dias} días.')
        else:
            messages.error(request, 'Duración inválida.')

        return redirect('home')  # Redirige a la lista de productos

    return render(request, 'destacar.html', {'producto': producto})


@csrf_exempt
@login_required
def toggle_favorito(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        producto_id = data.get('producto_id')
        
        try:
            producto = Producto.objects.get(id=producto_id)
            favorito, created = Favorito.objects.get_or_create(usuario=request.user, producto=producto)

            if not created:
                favorito.delete()
                return JsonResponse({'success': True, 'action': 'removed'})

            return JsonResponse({'success': True, 'action': 'added'})
        except Producto.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Producto no encontrado.'})
    return JsonResponse({'success': False, 'error': 'Método no permitido.'})


@user_passes_test(lambda u: u.is_superuser)
def eliminar_comentario(request, comentario_id):
    comentario = get_object_or_404(Comentario, id=comentario_id)
    producto_id = comentario.producto.id 
    comentario.delete()
    messages.success(request, "Comentario eliminado exitosamente.")
    return redirect('detalle_producto', producto_id=producto_id)


@login_required
def inbox(request):
    # Filtra las conversaciones del usuario
    conversations = Conversation.objects.filter(participants=request.user).distinct()

    # Obtén el otro participante para cada conversación
    user_conversations = []
    for conversation in conversations:
        other_participant = conversation.participants.exclude(id=request.user.id).first()
        if other_participant:
            last_message = conversation.messages.last()
            # Verifica si hay mensajes en la conversación
            if last_message:
                user_conversations.append({
                    'conversation': conversation,
                    'other_participant': other_participant,
                    'last_message': last_message,
                })
            else:
                # Si no hay mensajes, sigue agregando la conversación pero sin mensaje
                user_conversations.append({
                    'conversation': conversation,
                    'other_participant': other_participant,
                    'last_message': None,
                })

    return render(request, 'mensajeria/inbox.html', {'user_conversations': user_conversations})

from django.contrib.auth import logout

LISTA_AMARILLA = ['tonto', 'idiota', 'estupido', 'imbecil', 'pendejo', 'weon', 'huevon', 'pelotudo', 'tarado', 'inutil', 'baboso', 'bobo', 'burro', 'cobarde', 'cretino', 'desgraciado', 'desubicado', 'gil', 'ignorante', 'menso', 'necio', 'pajero', 'payaso', 'pesado', 'ridiculo', 'torpe', 'leso', 'sapo', 'barsa', 'flaite', 'ordinario', 'patetico', 'molesto', 'pesao', 'tontito', 'weona', 'huevona', 'pelotuda', 'tarada', 'babosa', 'boba', 'burra', 'cretina', 'mensa', 'payasa', 'ridicula', 'ordinaria', 'patetica', 'desagradable', 'odioso'] # Insultos leves
LISTA_ROJA = ['hijueputa', 'hijo de puta', 'hija de puta', 'conchetumadre', 'conchesumadre', 'concha tu madre', 'ctm', 'puta', 'puto', 'culiao', 'culiado', 'culiada', 'qliao', 'bastardo', 'bastarda', 'maldito', 'maldita', 'acosar', 'acoso', 'acosador', 'acosadora', 'amenaza', 'amenazar', 'amenazarte', 'matar', 'matarte', 'matarlo', 'matarla', 'asesinar', 'golpear', 'golpearte', 'agredir', 'agredirte', 'extorsion', 'extorsionar', 'chantaje', 'chantajear', 'hostigar', 'hostigamiento', 'estafar', 'estafador', 'estafadora', 'robar', 'ladron', 'ladrona', 'hacerte daño', 'te voy a matar', 'te voy a pegar', 'te voy a golpear', 'te voy a hacer daño'] # Faltas graves
    
def send_message(request, conversation_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        content = data.get('content')
        conversation = get_object_or_404(Conversation, id=conversation_id)

        if content:
            message = Message.objects.create(
                sender=request.user,
                content=content,
                conversation=conversation
            )
            
            conversation.hidden_by.clear() 

            texto_evaluar = content.lower()
            
            # re.search con \b asegura que solo busque la palabra COMPLETA y exacta
            es_roja = any(re.search(rf'\b{re.escape(palabra)}\b', texto_evaluar) for palabra in LISTA_ROJA)
            es_amarilla = any(re.search(rf'\b{re.escape(palabra)}\b', texto_evaluar) for palabra in LISTA_AMARILLA)

            admin_user = User.objects.filter(is_superuser=True).first() or request.user

            if es_roja:
                MessageReport.objects.create(
                    message=message,
                    reporter=admin_user,
                    reason="🚨 ALERTA ROJA (Sistema Automático): Detección de vocabulario extremadamente grave."
                )
                
                # Bloqueo Lógico: Desactivar la cuenta del infractor
                usuario_infractor = request.user
                usuario_infractor.is_active = False
                usuario_infractor.save()
                
                #  Destruir la sesión activa 
                logout(request)
                
                # Enviamos una respuesta 403 (Prohibido) al JavaScript
                return JsonResponse({
                    'banned': True,
                    'message': 'Tu cuenta ha sido suspendida por violar las normas de la comunidad.'
                }, status=403)

            elif es_amarilla:
                # Solo genera el reporte silencioso para que el admin lo revise después
                MessageReport.objects.create(
                    message=message,
                    reporter=admin_user,
                    reason="🟡 ALERTA AMARILLA (Sistema Automático): Detección de lenguaje ofensivo o spam."
                )

            print(f"Mensaje creado: {message.content}")
            return JsonResponse({'message': 'Mensaje enviado correctamente'})
            
        else:
            return JsonResponse({'error': 'El contenido del mensaje no puede estar vacío'}, status=400)
        
@login_required
def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id)
    other_participant = conversation.participants.exclude(id=request.user.id).first()  # Obtén al otro participante
    
    return render(request, 'mensajeria/conversation_detail.html', {
        'conversation': conversation,
        'other_participant': other_participant,  # Pasa el otro participante (el objeto User)
    })

@login_required
def start_conversation(request, recipient_id):
    recipient = get_object_or_404(User, id=recipient_id)

    # Verifica si ya existe una conversación entre comprador y vendedor
    conversation = Conversation.objects.filter(participants=request.user).filter(participants=recipient).first()

    if not conversation:
        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, recipient)

    return redirect('conversation_detail', conversation_id=conversation.id)


@login_required
def conversations_list(request):
    conversations = Conversation.objects.filter(participants=request.user).exclude(hidden_by=request.user).distinct()

    grouped_conversations = {}
    for conversation in conversations:
        other_participant = conversation.participants.exclude(id=request.user.id).first()

        if other_participant:
            unread_count = conversation.messages.filter(is_read=False).exclude(sender=request.user).count()
            conversation.unread_count = unread_count
            
            grouped_conversations.setdefault(other_participant, []).append(conversation)
    
    return render(request, 'mensajeria/conversations_list.html', {
        'grouped_conversations': grouped_conversations,
    })

def get_conversation_messages(request, conversation_id):
    # Obtén los mensajes de la conversación
    messages = Message.objects.filter(conversation_id=conversation_id).order_by('timestamp')

 
    unread_messages = messages.exclude(sender=request.user).filter(is_read=False)
    if unread_messages.exists():
        unread_messages.update(is_read=True)

    # Crea una lista de los mensajes para devolver en formato JSON
    message_data = [
        {
            'id': message.id,
            'sender': {
                'id': message.sender.id,
                'first_name': message.sender.first_name,
                'last_name': message.sender.last_name,
            },
            'content': message.content,
            'timestamp': message.timestamp.strftime('%d/%m/%Y %H:%M'), 
            'is_read': message.is_read  
        }
        for message in messages
    ]

    return JsonResponse({'messages': message_data})




class ProfileView(DetailView):
    model = User
    template_name = 'registration/profile.html'  # Plantilla para mostrar el perfil
    context_object_name = 'user'  # El contexto será llamado 'user' en la plantilla

    def get_object(self):
        return self.request.user
    

def lista_reportes(request):
    reportes = Reporte.objects.select_related('producto', 'usuario').all().order_by('-fecha_reporte')
    return render(request, 'reportes/lista_reportes.html', {'reportes': reportes})

@login_required
def reportar_producto(request, producto_id):
    if request.method == 'POST':
        producto = get_object_or_404(Producto, id=producto_id)
        motivo = request.POST.get('motivo', '').strip()
        
        if motivo:
            Reporte.objects.create(
                producto=producto,
                usuario=request.user,
                motivo=motivo
            )
            messages.success(request, 'El reporte ha sido enviado correctamente.')
            # Redirige a la vista del detalle del producto con el producto_id
            return redirect('detalle_producto', producto_id=producto.id)
        else:
            messages.error(request, 'Debes ingresar un motivo para reportar el producto.')

    return redirect('lista_productos') 


@login_required
def eliminar_reporte(request, reporte_id):
    reporte = get_object_or_404(Reporte, id=reporte_id)
    reporte.delete()
    messages.success(request, 'El reporte ha sido eliminado correctamente.')
    return redirect('lista_reportes') 



from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from .models import Comentario, MessageReport, ReporteComentario

@login_required
def reportar_comentario(request, comentario_id):
    if request.method == 'POST':
        motivo = request.POST.get('motivo')

        if not motivo or len(motivo.strip()) < 5:  # Asegúrate de que el motivo no esté vacío
            messages.error(request, "El motivo del reporte es obligatorio y debe tener al menos 5 caracteres.")
            return redirect('home')

        comentario = get_object_or_404(Comentario, id=comentario_id)  # Busca el comentario por su ID

        # Crea el reporte
        ReporteComentario.objects.create(
            comentario=comentario,
            usuario=request.user,
            motivo=motivo
        )

        messages.success(request, 'El comentario ha sido reportado correctamente.')

        # Redirige al detalle del producto
        return redirect('detalle_producto', producto_id=comentario.producto.id)

    return redirect('home')


@login_required
def listar_reportes_comentarios(request):
    # Obtener todos los reportes de comentarios
    reportes_comentarios = ReporteComentario.objects.all().order_by('-fecha_creacion')
    return render(request, 'reportes/reportes_cometario.html', {
        'reportes_comentarios': reportes_comentarios
    })


@login_required
def eliminar_reporte_comentario(request, reporte_id):
    if request.user.is_staff:
        reporte = get_object_or_404(ReporteComentario, id=reporte_id)
        reporte.delete()
        messages.success(request, 'El reporte ha sido eliminado correctamente.')
    return redirect('reportes_comentarios')


class DeleteAccountView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        user = request.user
        user.delete()
        return redirect('home')
    

#desde aqui empiezo a probar cosas nuevas 
import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import MessageReport, Message
@login_required
def report_message(request, message_id):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        reason = data.get('reason', 'Sin motivo especificado')
        message = get_object_or_404(Message, id=message_id)
        
        MessageReport.objects.create(message=message, reporter=request.user, reason=reason)
        return JsonResponse({'status': 'Denuncia enviada al administrador exitosamente'})
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


# 2. NUEVA Función para MOSTRAR la tabla de reportes
@login_required
def lista_reportes_mensajes(request):
    if not request.user.is_staff:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    # Separamos los reportes usando el campo 'resolved'
    reportes_pendientes = MessageReport.objects.filter(resolved=False).order_by('-fecha_creacion')
    reportes_resueltos = MessageReport.objects.filter(resolved=True).order_by('-fecha_creacion')
    
    return render(request, 'reportes/reportes_mensajes.html', {
        'reportes_pendientes': reportes_pendientes,
        'reportes_resueltos': reportes_resueltos
    })

from django.shortcuts import redirect

@login_required
def resolver_reporte_mensaje(request, reporte_id):
    if not request.user.is_staff:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    if request.method == 'POST':
        reporte = get_object_or_404(MessageReport, id=reporte_id)
        reporte.resolved = True  # Cambiamos el estado
        reporte.save()
        
    return redirect('lista_reportes_mensajes')

@login_required
def eliminar_reporte_mensaje(request, reporte_id):
    # Verificamos que solo el staff pueda borrar reportes
    if not request.user.is_staff:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    # Como el modal usa un formulario POST, nos aseguramos de que la petición sea POST
    if request.method == 'POST':
        # Buscamos el reporte y lo eliminamos
        reporte = get_object_or_404(MessageReport, id=reporte_id)
        reporte.delete()
        
    # Recargamos la página de la tabla
    return redirect('lista_reportes_mensajes')


@login_required
def ocultar_conversacion(request, conversation_id):
    if request.method == 'POST':
        conversation = get_object_or_404(Conversation, id=conversation_id)
        # Añadimos al usuario actual a la lista de ocultos
        conversation.hidden_by.add(request.user)
        
    return redirect('conversations_list')

@login_required
def contar_mensajes_no_leidos(request):
    cantidad = Message.objects.filter(
        conversation__participants=request.user,
        is_read=False
    ).exclude(sender=request.user).count()
    
    return JsonResponse({'unread_count': cantidad})

@login_required
def gestion_usuarios(request):
    # Protección estricta: Solo los superusuarios pueden entrar aquí
    if not request.user.is_superuser:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    # Traemos los usuarios activos, EXCLUYENDO al administrador actual
    usuarios_activos = User.objects.filter(is_active=True).exclude(id=request.user.id).order_by('-date_joined')
    
    # Traemos los usuarios suspendidos/baneados
    usuarios_baneados = User.objects.filter(is_active=False).order_by('-date_joined')
    
    return render(request, 'reportes/gestion_usuarios.html', {
        'usuarios_activos': usuarios_activos,
        'usuarios_baneados': usuarios_baneados
    })

@login_required
def cambiar_estado_usuario(request, user_id):
    if not request.user.is_superuser:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
        
    if request.method == 'POST':
        usuario = get_object_or_404(User, id=user_id)
        # Doble verificación para no afectar al admin actual
        if usuario.id != request.user.id:
            usuario.is_active = not usuario.is_active # Invierte el estado (Si era True, pasa a False y viceversa)
            usuario.save()
            
    return redirect('gestion_usuarios')

@login_required
def eliminar_usuario_definitivo(request, user_id):
    if not request.user.is_superuser:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
        
    if request.method == 'POST':
        usuario = get_object_or_404(User, id=user_id)
        if usuario.id != request.user.id:
            usuario.delete() # Borrado real de la base de datos
            
    return redirect('gestion_usuarios')