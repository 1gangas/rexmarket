document.addEventListener("DOMContentLoaded", function() {
    
    /* =======================================================
       1. BÚSQUEDA EN TIEMPO REAL OPTIMIZADA (DEBOUNCING)
    ======================================================= */
    const searchInput = document.querySelector('input[type="search"][name="q"]');
    const productosContenedor = document.getElementById('lista-productos');
    let timeoutId; // Variable para controlar el tiempo

    if (searchInput && productosContenedor) {
        searchInput.addEventListener('input', function () {
            const query = this.value.trim();

            // 1. Cancelar la búsqueda anterior si el usuario sigue tecleando rápido
            clearTimeout(timeoutId);

            // 2. Esperar 300 milisegundos después de que el usuario deje de escribir
            timeoutId = setTimeout(() => {
                
                // Efecto visual: opacar ligeramente los productos mientras carga
                productosContenedor.style.opacity = '0.5';
                productosContenedor.style.transition = 'opacity 0.2s ease';

                // Armar la URL correctamente manteniendo otros filtros si existen
                const url = new URL(window.location.href);
                if (query.length > 0) {
                    url.searchParams.set('q', query);
                } else {
                    url.searchParams.delete('q'); // Si está vacío, quita la variable de búsqueda
                }

                // Hacer la petición al servidor
                fetch(url.toString())
                    .then(response => response.text())
                    .then(html => {
                        // Extraer solo la lista de productos del HTML que llegó
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(html, 'text/html');
                        const nuevosProductos = doc.querySelector('#lista-productos');

                        if (nuevosProductos) {
                            // Actualizar el HTML sin recargar la página completa
                            productosContenedor.innerHTML = nuevosProductos.innerHTML;
                        }
                    })
                    .catch(error => console.error('Error al buscar productos:', error))
                    .finally(() => {
                        // Quitar el efecto visual de carga
                        productosContenedor.style.opacity = '1';
                    });
            }, 300); // 300ms es el estándar de la industria para el "debounce"
        });
    }

    /* =======================================================
       2. AUTO-FOCO INTELIGENTE PARA MODALES DE BOOTSTRAP 5
    ======================================================= */
    // En lugar de buscar un ID específico que podría no existir, 
    // buscamos TODOS los modales y le damos foco al primer input automáticamente.
    const modals = document.querySelectorAll('.modal');
    
    modals.forEach(modal => {
        modal.addEventListener('shown.bs.modal', function () {
            // Busca el primer campo de texto dentro del modal que se acaba de abrir
            const firstInput = this.querySelector('input:not([type="hidden"]), textarea');
            if (firstInput) {
                firstInput.focus();
            }
        });
    });

});