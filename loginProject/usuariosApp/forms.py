from django import forms
from usuariosApp.models import Producto
from django.core.validators import RegexValidator
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from usuariosApp.models import Comentario
import re
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from itertools import cycle

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'descripcion', 'precio', 'imagen', 'categoria']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Clase CSS genérica para los campos
        default_classes = 'form-control'
        # Diccionario para definir clases específicas por campo
        field_classes = {
            'imagen': 'form-control-file',
        }

        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = field_classes.get(field_name, default_classes)

    # Validación personalizada para imagen
    imagen = forms.ImageField(
        required=True,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        error_messages={
            'required': 'La imagen del producto es obligatoria.',
            'invalid': 'Sube una imagen válida.',
        }
    )

    # Validación personalizada para categoría
    categoria = forms.ChoiceField(
        choices=Producto.CATEGORIAS,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        error_messages={
            'required': 'Selecciona una categoría válida.',
        }
    )

    # Validación personalizada para precio
    precio = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Precio'}),
        validators=[
            RegexValidator(
                r'^\d{1,3}(?:[.,]\d{3})*(?:,\d+)?$',
                'El precio debe ser un número válido (usa coma para los decimales y puntos para miles).'
            )
        ]
    )

    # Validación adicional para nombre
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if not nombre or len(nombre) < 3:
            raise forms.ValidationError("El nombre del producto debe tener al menos 3 caracteres.")
        if nombre[0] != nombre[0].upper():
            raise forms.ValidationError("El nombre debe comenzar con una letra mayúscula.")
        return nombre

    # Validación adicional para descripción
    def clean_descripcion(self):
        descripcion = self.cleaned_data.get('descripcion')
        if not descripcion or len(descripcion) < 10:
            raise forms.ValidationError("La descripción debe tener al menos 10 caracteres.")
        return descripcion

    # Validación adicional para precio (ejemplo de lógica específica)
    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        # Reemplazar puntos y comas para validar numéricamente
        precio_normalizado = precio.replace('.', '').replace(',', '.')
        try:
            precio_float = float(precio_normalizado)
            if precio_float <= 0:
                raise forms.ValidationError("El precio debe ser un valor mayor que 0.")
        except ValueError:
            raise forms.ValidationError("El precio debe ser un número válido.")
        return precio



def validar_rut(rut):
    rut = rut.upper().strip() 
    rut = rut.replace(".", "").replace("-", "")  
    
    if len(rut) < 2:
        return False

    cuerpo, dv = rut[:-1], rut[-1:]

    # Calcular el dígito verificador
    revertido = map(int, reversed(cuerpo))
    factors = cycle(range(2, 8))  
    s = sum(d * f for d, f in zip(revertido, factors))
    
    res = (-s) % 11
    
    if str(res) == dv:
        return True
    elif dv == "K" and res == 10:
        return True
    return False


# Formulario de registro personalizado en Django
class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'username', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    # Validación del username (RUT)
    # Validación y Formateo del username (RUT)
    def clean_username(self):
        username = self.cleaned_data.get('username')

        if not username:
            return username

        # 1. Limpiamos cualquier punto o guion extra que el usuario haya puesto
        rut_limpio = username.upper().replace(".", "").replace("-", "").strip()

        # 2. Verificamos si es un RUT matemáticamente válido
        if not self.validar_rut(rut_limpio):
            raise ValidationError("El RUT ingresado no es válido.")

        # 3. Separamos el cuerpo del dígito verificador para forzar el formato exacto
        cuerpo = rut_limpio[:-1]
        dv = rut_limpio[-1]
        rut_formateado = f"{cuerpo}-{dv}"

        # 4. Retornamos el RUT ya formateado (Ej: 12345678-9)
        return rut_formateado

    def validar_rut(self, rut: str) -> bool:
        return validar_rut(rut)

    # Validación del campo first_name
    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not first_name:
            raise ValidationError("Este campo es obligatorio.")

        # Verificar que la primera letra sea mayúscula
        if first_name[0] != first_name[0].upper():
            raise ValidationError("El nombre debe comenzar con una letra mayúscula.")

        return first_name
    
    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not last_name:
            raise ValidationError("Este campo es obligatorio.")

        # Verificar que la primera letra sea mayúscula
        if last_name[0] != last_name[0].upper():
            raise ValidationError("El apellido debe comenzar con una letra mayúscula.")

        return last_name
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        if not email:
            raise ValidationError("Este campo es obligatorio.")
        
        # 1. Verificar el formato básico del email
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            raise ValidationError("El formato del email ingresado no es válido.")
            
        # 2. NUEVO: Verificar que sea correo institucional de INACAP
        if not email.lower().endswith('@inacapmail.cl'):
            raise ValidationError("Para registrarte en RexMarket debes usar tu correo institucional.")
            
        # 3. EXTRA PRO: Verificar que el correo no esté ya registrado en la base de datos
        from django.contrib.auth.models import User
        if User.objects.filter(email=email).exists():
            raise ValidationError("Este correo institucional ya está registrado en el sistema.")
        
        return email

    def clean(self):
        # Llama a la validación original de Django primero
        cleaned_data = super().clean()
        
        # Obtenemos ambas contraseñas
        password = cleaned_data.get("password1")
        password_confirm = cleaned_data.get("password2")

        # Verificamos si ambas fueron ingresadas y si son diferentes
        if password and password_confirm and password != password_confirm:
            # Agregamos el error personalizado en español al segundo campo
            self.add_error('password2', "Las contraseñas no coinciden. Por favor, inténtalo de nuevo.")

        return cleaned_data




class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['comentario', 'valoracion']
        widgets = {
            'comentario': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'valoracion': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
        }