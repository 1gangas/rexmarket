from django.db import models
from django.contrib.auth.models import User
import uuid
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.timezone import now
from django.core.mail import send_mail
from django.conf import settings



class Producto(models.Model):
    CATEGORIAS = [
    ('Comida y Bebidas', 'Comida y Bebidas'),      
    ('POSTRES', 'Postres y Dulces'),            
    ('TECNOLOGIA', 'Tecnología y accesorios'),    
    ('ROPA', 'Ropa y Moda'),                     
    ('ACCESORIOS', 'Accesorios'),                
    ('LIBROS_PAPELERIA', 'Libros y Papelería'),  
    ('MANUALIDADES', 'Manualidades'),           
    ('SERVICIOS', 'Servicios'),                  
    ('HOGAR', 'Hogar y Decoración'),           
    ('ENTRETENIMIENTO', 'Juegos y Entretenimiento'),  
    ('DEPORTES', 'Deportes y Fitness'),          
    ('OTROS', 'Otros'),                          
]
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio = models.CharField(max_length=20) 
    imagen = models.ImageField(upload_to='productos/')
    vendedor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='productos')
    categoria = models.CharField(max_length=30, choices=CATEGORIAS, default='OTROS')
    destacado_hasta = models.DateTimeField(null=True, blank=True)  
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre
    
    def es_destacado(self):
        return self.destacado_hasta and self.destacado_hasta > now()
    
    def es_favorito(self, usuario):
        if usuario.is_authenticated:
            return self.favoritos.filter(usuario=usuario).exists()
        return False

    

class VerificationCode(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=36, default=uuid.uuid4)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {'Verificado' if self.is_verified else 'No verificado'}"
    


class Comentario(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='comentarios')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    comentario = models.TextField()
    valoracion = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.usuario.username} - {self.producto.nombre}'
    

class Favorito(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favoritos')
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE, related_name='favoritos')
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'producto')  # Evita duplicados

    def __str__(self):
        return f"{self.usuario.username} - {self.producto.nombre}"
    
class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    hidden_by = models.ManyToManyField(User, related_name='hidden_conversations', blank=True)

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']  


class Reporte(models.Model):
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE, related_name='reportes')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reportes')
    motivo = models.TextField()
    fecha_reporte = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Reporte de {self.usuario.first_name} sobre {self.producto.nombre}"
    

class ReporteComentario(models.Model):
    comentario = models.ForeignKey(Comentario, on_delete=models.CASCADE, related_name='reportes')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    motivo = models.TextField()
    fecha_creacion =models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Reporte de {self.usuario.username} sobre el comentario de {self.comentario.producto.nombre}'
    
from django.db import models
from django.contrib.auth.models import User

class MessageReport(models.Model):
    message = models.ForeignKey(Message, related_name='reports', on_delete=models.CASCADE)
    reporter = models.ForeignKey(User, related_name='submitted_reports', on_delete=models.CASCADE)
    reason = models.TextField() 
    fecha_creacion = models.DateTimeField(auto_now_add=True) 
    resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Reporte de {self.reporter.username} - Resuelto: {self.resolved}"