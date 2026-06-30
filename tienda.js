// ============================================
// CONFIGURACIÓN SUPABASE — EDITAR AQUÍ
// ============================================
const SUPABASE_URL = 'https://lijzftjgevwnjorpycxa.supabase.co';
const SUPABASE_KEY = 'sb_publishable_Y1v63ZdMakSGbx449TKpiA_cKNykbk2';

// ============================================
// CONFIGURACIÓN STRIPE
// ============================================
const STRIPE_PUBLISHABLE_KEY = 'pk_test_51TnmgfFdVhr9yKQz8kf7NbBhWPUcP9wHyW99jZMTRVtxbsEZqOdu7hYulPgaMbM76o8F59uHPdSSFtlx3b6BouFr00BmQ5mKah';
// Edge Function URL (se genera al hacer deploy)
const STRIPE_EDGE_FUNCTION = SUPABASE_URL + '/functions/v1/swift-endpoint';

// ============================================
// ESTADO GLOBAL
// ============================================
let supabaseClient = null;
let currentUser = null;
let productosData = [];
let carritoItems = [];
let perfilesData = {};
let pedidosData = [];
let stripeInstance = null;
let cardElement = null;
let currentView = 'vista-inicio';
let categoriaActiva = 'todas';
let pendingProductoId = null;

// ============================================
// INICIALIZACIÓN SUPABASE
// ============================================
function getSupabase() {
  if (supabaseClient) return supabaseClient;

  if (!window.supabase || !window.supabase.createClient) {
    throw new Error('Supabase no se cargó correctamente. Verifica tu conexión a internet.');
  }

  supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
  return supabaseClient;
}

// ============================================
// UTILIDADES
// ============================================
function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatMoney(amount) {
  return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(amount);
}

function setButtonLoading(button, isLoading, loadingText) {
  if (!button) return;
  if (isLoading) {
    button.dataset.originalHtml = button.innerHTML;
    button.disabled = true;
    button.innerHTML = loadingText || 'Cargando...';
  } else {
    button.disabled = false;
    if (button.dataset.originalHtml) {
      button.innerHTML = button.dataset.originalHtml;
    }
  }
}

function showToast(message, type, duration) {
  var container = document.getElementById('toast-container');
  if (!container) return;

  type = type || 'info';
  duration = duration || 2800;

  var iconMap = { success: 'check_circle', error: 'error', info: 'info' };

  var toast = document.createElement('div');
  toast.className = 'toast toast-' + type;
  toast.innerHTML =
    '<span class="material-symbols-outlined">' + (iconMap[type] || 'info') + '</span>' +
    '<span>' + escapeHtml(message) + '</span>';

  container.appendChild(toast);
  requestAnimationFrame(function () { toast.classList.add('show'); });

  setTimeout(function () {
    if (!toast.isConnected) return;
    toast.classList.add('hide');
    toast.classList.remove('show');
    setTimeout(function () { toast.remove(); }, 350);
  }, duration);
}

function getFotoProducto(codigo) {
  if (!codigo) return getFotoPlaceholder();
  return SUPABASE_URL + '/storage/v1/object/public/productos_fotos/' + codigo + '.png';
}

function getFotoPlaceholder() {
  return 'data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">' +
    '<rect width="400" height="300" fill="#F1F5F9"/>' +
    '<text x="200" y="140" text-anchor="middle" fill="#CBD5E1" font-family="system-ui" font-size="14" font-weight="500">Sin imagen</text>' +
    '<text x="200" y="165" text-anchor="middle" fill="#CBD5E1" font-family="system-ui" font-size="36">🖼</text>' +
    '</svg>'
  );
}

function buildImgOnError(codigo) {
  var jpgUrl = SUPABASE_URL + '/storage/v1/object/public/productos_fotos/' + codigo + '.jpg';
  var placeholder = getFotoPlaceholder();
  return "if(!this.dataset.retried){this.dataset.retried='1';this.src='" + jpgUrl + "';}else{this.onerror=null;this.src='" + placeholder + "';}";
}

// ============================================
// AUTENTICACIÓN
// ============================================
function initAuth() {
  var supabase = getSupabase();

  supabase.auth.onAuthStateChange(function (event, session) {
    currentUser = session ? session.user : null;

    if (event === 'SIGNED_IN') {
      if (pendingProductoId) {
        var prodId = pendingProductoId;
        pendingProductoId = null;
        addToCart(prodId).then(function () {
          showToast('Producto agregado al carrito.', 'success');
        }).catch(function (err) {
          console.error(err);
          showToast('Error al agregar al carrito.', 'error');
        });
      }
      cargarPerfil();
      cargarHistorialPedidos();
    }

    if (event === 'SIGNED_OUT') {
      perfilesData = {};
      pedidosData = [];
    }

    updateNavbar();
    loadCarrito();
    renderCarrito();
    renderPerfil();
  });

  supabase.auth.getSession().then(function (result) {
    if (result.data && result.data.session) {
      currentUser = result.data.session.user;
      cargarPerfil();
      cargarHistorialPedidos();
    }
    updateNavbar();
    loadCarrito().then(function () {
      renderCarrito();
      renderPerfil();
    });
  }).catch(function (err) {
    console.error('Error al obtener sesión:', err);
  });
}

function traducirErrorAuth(err) {
  var msg = (err && err.message) ? String(err.message) : '';
  var lower = msg.toLowerCase();
  if (/invalid login credentials/i.test(msg)) return 'Correo o contraseña incorrectos.';
  if (/user already registered/i.test(msg)) return 'Ya existe una cuenta con ese correo. Inicia sesión.';
  if (/email not confirmed/i.test(msg)) return 'Confirma tu correo antes de iniciar sesión. Revisa tu bandeja.';
  if (/password.*weak/i.test(msg) || /password.*short/i.test(msg)) return 'La contraseña debe tener al menos 8 caracteres.';
  if (/failed to fetch|network/i.test(msg)) return 'Sin conexión. Verifica tu internet.';
  return msg || 'Error inesperado. Intenta de nuevo.';
}

async function loginUser(email, password) {
  var btn = document.getElementById('btn-login-submit');
  var errorEl = document.getElementById('login-error');
  try {
    setButtonLoading(btn, true, 'Ingresando...');
    if (errorEl) { errorEl.classList.remove('show'); errorEl.textContent = ''; }

    var result = await getSupabase().auth.signInWithPassword({ email: email, password: password });

    if (result.error) throw result.error;

    closeAuthModal();
    showToast('Bienvenido de vuelta.', 'success');
  } catch (err) {
    console.error('Login error:', err);
    if (errorEl) { errorEl.textContent = traducirErrorAuth(err); errorEl.classList.add('show'); }
  } finally {
    setButtonLoading(btn, false);
  }
}

async function registerUser(nombre, apellidos, telefono, ciudad, email, password) {
  var btn = document.getElementById('btn-register-submit');
  var errorEl = document.getElementById('register-error');
  try {
    setButtonLoading(btn, true, 'Creando cuenta...');
    if (errorEl) { errorEl.classList.remove('show'); errorEl.textContent = ''; }

    if (!ciudad) {
      if (errorEl) { errorEl.textContent = 'Selecciona tu ciudad para continuar.'; errorEl.classList.add('show'); }
      return;
    }

    var result = await getSupabase().auth.signUp({ email: email, password: password });

    if (result.error) throw result.error;

    if (result.data && result.data.user) {
      try {
        await getSupabase().from('perfiles')
          .update({
            nombre: nombre,
            apellidos: apellidos,
            telefono: telefono,
            ciudad: ciudad,
          })
          .eq('id', result.data.user.id);
      } catch (perfilErr) {
        console.warn('No se pudo actualizar el perfil:', perfilErr);
      }
    }

    closeAuthModal();
    showToast('Cuenta creada exitosamente. Bienvenido.', 'success');
  } catch (err) {
    console.error('Register error:', err);
    if (errorEl) { errorEl.textContent = traducirErrorAuth(err); errorEl.classList.add('show'); }
  } finally {
    setButtonLoading(btn, false);
  }
}

async function logoutUser() {
  try {
    await getSupabase().auth.signOut();
    currentUser = null;
    carritoItems = [];
    updateNavbar();
    renderCarrito();
    switchView('vista-inicio');
    showToast('Sesión cerrada.', 'info');
  } catch (err) {
    console.error('Logout error:', err);
    showToast('Error al cerrar sesión.', 'error');
  }
}

function openAuthModal(pendingProdId) {
  if (pendingProdId) {
    pendingProductoId = pendingProdId;
  }

  var overlay = document.getElementById('auth-overlay');
  if (!overlay) return;
  overlay.classList.remove('hidden');
  requestAnimationFrame(function () {
    overlay.classList.add('show');
  });
  document.body.style.overflow = 'hidden';
}

function closeAuthModal() {
  var overlay = document.getElementById('auth-overlay');
  if (!overlay) return;
  overlay.classList.remove('show');
  setTimeout(function () {
    overlay.classList.add('hidden');
    document.body.style.overflow = '';
  }, 300);
}

// ============================================
// PRODUCTOS
// ============================================
async function cargarCatalogo() {
  var container = document.getElementById('catalogo-container');
  if (!container) return;

  showCatalogoSkeleton();

  try {
    var result = await getSupabase().from('productos').select('*').order('id', { ascending: true });

    console.log('Supabase productos response:', { error: result.error, status: result.status, count: result.count, dataLength: result.data ? result.data.length : 0 });

    if (result.error) throw result.error;

    if (!result.data || result.data.length === 0) {
      console.warn('productos: tabla vacía o RLS bloqueando. Verifica en Supabase Table Editor que la tabla tenga filas.');
      productosData = [];
      container.innerHTML =
        '<div class="col-span-full empty-state">' +
        '<span class="material-symbols-outlined">inventory_2</span>' +
        '<p class="text-[#64748B] font-medium mb-1">Catálogo sin productos</p>' +
        '<p class="text-[#94A3B8] text-[.875rem] mb-4 max-w-[36ch] text-balance">Si ya insertaste productos, revisa que la política RLS permita lecturas anónimas: <code class="bg-[#F1F5F9] px-1.5 py-0.5 rounded text-[#1E293B] text-[.75rem]">CREATE POLICY "anon lee productos" ON productos FOR SELECT TO anon USING (true);</code></p>' +
        '<button class="btn-outline h-10 px-5 text-[.8125rem]" onclick="cargarCatalogo()">' +
        '<span class="material-symbols-outlined" style="font-size:18px">refresh</span> Reintentar' +
        '</button>' +
        '</div>';
      renderCategoriaChips();
      return;
    }

    productosData = result.data;
    renderCategoriaChips();
    renderCatalogo();
  } catch (err) {
    console.error('Error al cargar catálogo:', err);
    container.innerHTML =
      '<div class="col-span-full empty-state">' +
      '<span class="material-symbols-outlined" style="color:#FCA5A5">error</span>' +
      '<p class="text-[#64748B] font-medium mb-1">Error al cargar el catálogo</p>' +
      '<p class="text-[#94A3B8] text-[.875rem] mb-4">Verifica tu conexión e intenta de nuevo.</p>' +
      '<button class="btn-outline h-10 px-5 text-[.8125rem]" onclick="cargarCatalogo()">Reintentar</button>' +
      '</div>';
    showToast('Error al cargar productos.', 'error');
  }
}

function showCatalogoSkeleton() {
  var container = document.getElementById('catalogo-container');
  if (!container) return;
  var skeletons = [];
  for (var i = 0; i < 8; i++) {
    skeletons.push(
      '<div class="rounded-[1.25rem] overflow-hidden bg-white border border-[rgba(0,0,0,.04)]">' +
      '<div class="skeleton aspect-[4/3]" style="border-radius:0"></div>' +
      '<div class="p-4 space-y-3">' +
      '<div class="skeleton h-3 w-16 rounded-full"></div>' +
      '<div class="skeleton h-4 w-full rounded-md"></div>' +
      '<div class="flex items-baseline gap-2">' +
      '<div class="skeleton h-6 w-20 rounded-md"></div>' +
      '<div class="skeleton h-4 w-14 rounded-md"></div>' +
      '</div>' +
      '<div class="flex items-center justify-between">' +
      '<div class="skeleton h-5 w-24 rounded-full"></div>' +
      '<div class="skeleton h-11 w-11 rounded-full"></div>' +
      '</div>' +
      '</div>' +
      '</div>'
    );
  }
  container.innerHTML = skeletons.join('');
}

function getCategoriasUnicas() {
  var cats = new Set();
  productosData.forEach(function (p) {
    if (p.categoria) cats.add(p.categoria);
  });
  return Array.from(cats).sort();
}

function getFilteredProductos() {
  if (categoriaActiva === 'todas') return productosData;
  return productosData.filter(function (p) {
    return p.categoria === categoriaActiva;
  });
}

// ============================================
// PERFIL E HISTORIAL DE PEDIDOS
// ============================================
async function cargarPerfil() {
  if (!currentUser) return;
  try {
    var result = await getSupabase()
      .from('perfiles')
      .select('nombre, apellidos, telefono, ciudad')
      .eq('id', currentUser.id)
      .maybeSingle();

    if (result.error && result.error.code !== 'PGRST116') {
      console.warn('Error al cargar perfil:', result.error);
    }

    perfilesData = result.data || {};
  } catch (err) {
    console.warn('Error al cargar perfil:', err);
    perfilesData = {};
  }
}

async function cargarHistorialPedidos() {
  if (!currentUser) return;
  try {
    var movsResult = await getSupabase()
      .from('movimientos')
      .select('id, monto, estado, created_at')
      .eq('usuario_id', currentUser.id)
      .order('created_at', { ascending: false })
      .limit(20);

    if (movsResult.error) throw movsResult.error;

    var movimientos = movsResult.data || [];

    if (movimientos.length === 0) {
      pedidosData = [];
      return;
    }

    var movIds = movimientos.map(function (m) { return m.id; });

    var detResult = await getSupabase()
      .from('detalles_movimiento')
      .select('movimiento_id, producto_id, cantidad, precio_unitario')
      .in('movimiento_id', movIds);

    if (detResult.error) throw detResult.error;

    var detalles = detResult.data || [];
    var detallesPorMov = {};
    detalles.forEach(function (d) {
      if (!detallesPorMov[d.movimiento_id]) detallesPorMov[d.movimiento_id] = [];
      detallesPorMov[d.movimiento_id].push(d);
    });

    pedidosData = movimientos.map(function (mov) {
      var dets = detallesPorMov[mov.id] || [];
      return {
        id: mov.id,
        monto: mov.monto,
        estado: mov.estado,
        fecha: mov.created_at,
        cantidadProductos: dets.reduce(function (s, d) { return s + d.cantidad; }, 0),
        detalles: dets,
      };
    });
  } catch (err) {
    console.error('Error al cargar historial:', err);
    pedidosData = [];
  }
}

function renderPerfil() {
  var card = document.getElementById('perfil-card');
  var emailDisplay = document.getElementById('perfil-email-display');
  var histContainer = document.getElementById('historial-pedidos-container');

  if (!card) return;

  if (!currentUser) {
    card.innerHTML =
      '<div class="empty-state py-6">' +
      '<span class="material-symbols-outlined">person_off</span>' +
      '<p class="text-[#64748B] font-medium mb-1">No has iniciado sesión</p>' +
      '<p class="text-[#94A3B8] text-[.875rem] mb-4">Inicia sesión para ver tu perfil y pedidos.</p>' +
      '<button class="btn-brand h-11 px-6 text-[.875rem]" id="btn-login-from-profile">' +
      '<span class="material-symbols-outlined" style="font-size:18px">login</span> Iniciar Sesión' +
      '</button>' +
      '</div>';
    if (emailDisplay) emailDisplay.textContent = 'Inicia sesión para acceder a tu cuenta.';
    if (histContainer) histContainer.innerHTML =
      '<div class="empty-state py-6">' +
      '<span class="material-symbols-outlined">receipt_long</span>' +
      '<p class="text-[#94A3B8] text-[.875rem]">Tus compras aparecerán aquí.</p>' +
      '</div>';
    return;
  }

  var nombre = perfilesData.nombre || '';
  var apellidos = perfilesData.apellidos || '';
  var telefono = perfilesData.telefono || '';
  var ciudad = perfilesData.ciudad || '';
  var nombreCompleto = (nombre + ' ' + apellidos).trim();
  var iniciales = nombreCompleto
    ? nombreCompleto.split(' ').filter(Boolean).slice(0, 2).map(function (p) { return p[0].toUpperCase(); }).join('')
    : (currentUser.email || '?').charAt(0).toUpperCase();

  if (emailDisplay) emailDisplay.textContent = currentUser.email || '';

  card.innerHTML =
    '<div class="flex items-start gap-4">' +
      '<div class="perfil-avatar">' + escapeHtml(iniciales) + '</div>' +
      '<div class="flex-1 min-w-0">' +
        '<h3 class="font-bold text-[1.125rem] text-[#1E293B]">' + escapeHtml(nombreCompleto || 'Sin nombre') + '</h3>' +
        '<p class="text-[#64748B] text-[.8125rem] mt-0.5">' + escapeHtml(currentUser.email || '') + '</p>' +
        '<div class="flex flex-wrap gap-3 mt-3">' +
          (ciudad ? '<span class="perfil-dato"><span class="material-symbols-outlined">location_on</span>' + escapeHtml(ciudad) + '</span>' : '') +
          (telefono ? '<span class="perfil-dato"><span class="material-symbols-outlined">call</span>' + escapeHtml(telefono) + '</span>' : '') +
        '</div>' +
      '</div>' +
    '</div>';

  if (!histContainer) return;

  if (pedidosData.length === 0) {
    histContainer.innerHTML =
      '<div class="empty-state py-6">' +
      '<span class="material-symbols-outlined">receipt_long</span>' +
      '<p class="text-[#94A3B8] text-[.875rem]">Aún no tienes pedidos. Explora el catálogo.</p>' +
      '</div>';
    return;
  }

  histContainer.innerHTML = pedidosData.map(function (pedido) {
    var fechaStr = new Date(pedido.fecha).toLocaleDateString('es-MX', {
      day: 'numeric', month: 'short', year: 'numeric',
    });

    return (
      '<div class="pedido-card" data-pedido-id="' + pedido.id + '">' +
        '<div class="flex items-center justify-between">' +
          '<div>' +
            '<p class="font-semibold text-[.9375rem] text-[#1E293B]">Pedido #' + pedido.id + '</p>' +
            '<p class="text-[#64748B] text-[.75rem] mt-0.5">' +
              pedido.cantidadProductos + ' producto' + (pedido.cantidadProductos !== 1 ? 's' : '') +
              ' · ' + fechaStr +
            '</p>' +
          '</div>' +
          '<div class="text-right">' +
            '<p class="font-bold text-[1.0625rem] text-[#1E293B]">' + formatMoney(pedido.monto) + '</p>' +
            '<span class="pedido-estado-pagado">' +
              '<span class="material-symbols-outlined" style="font-size:12px">check</span>' +
              escapeHtml(pedido.estado || 'pagado') +
            '</span>' +
          '</div>' +
        '</div>' +
        '<div class="pedido-detalle hidden" id="pedido-detalle-' + pedido.id + '">' +
          pedido.detalles.map(function (d) {
            var prod = productosData.find(function (p) { return String(p.id) === String(d.producto_id); });
            var nombreProd = prod ? prod.nombre : ('Producto #' + d.producto_id);
            return (
              '<div class="flex items-center justify-between py-1.5 border-b border-[#E2E8F0] last:border-0">' +
                '<span class="text-[.8125rem] text-[#64748B]">' +
                  escapeHtml(nombreProd) + ' x' + d.cantidad +
                '</span>' +
                '<span class="text-[.8125rem] font-semibold text-[#1E293B]">' +
                  formatMoney(d.precio_unitario * d.cantidad) +
                '</span>' +
              '</div>'
            );
          }).join('') +
        '</div>' +
      '</div>'
    );
  }).join('');
}

async function togglePedidoDetalle(pedidoId) {
  var detalle = document.getElementById('pedido-detalle-' + pedidoId);
  if (!detalle) return;
  detalle.classList.toggle('hidden');
}

// ============================================
// CARRITO
// ============================================
async function loadCarrito() {
  if (!currentUser) {
    carritoItems = [];
    updateCartBadge();
    return;
  }

  try {
    var result = await getSupabase()
      .from('carrito')
      .select('id, cantidad, producto_id')
      .eq('usuario_id', currentUser.id);

    if (result.error) {
      if (result.error.code === 'PGRST116' || result.error.code === '42501') {
        console.warn('RLS bloquea carrito. Ejecuta: CREATE POLICY ON carrito FOR ALL TO authenticated USING (auth.uid() = usuario_id) WITH CHECK (auth.uid() = usuario_id);');
      }
      throw result.error;
    }

    var rawItems = result.data || [];

    carritoItems = rawItems.map(function (item) {
      var producto = productosData.find(function (p) { return String(p.id) === String(item.producto_id); });
      return {
        id: item.id,
        producto_id: item.producto_id,
        cantidad: item.cantidad,
        producto: producto || null,
      };
    }).filter(function (item) { return item.producto !== null; });

  } catch (err) {
    console.error('Error al cargar carrito:', err);
    carritoItems = [];
  }

  updateCartBadge();
}

async function addToCart(productoId) {
  if (!currentUser) {
    openAuthModal(productoId);
    return;
  }

  try {
    console.log('addToCart: currentUser.id =', currentUser.id, ', productoId =', productoId);
    var existing = carritoItems.find(function (item) { return String(item.producto_id) === String(productoId); });

    if (existing) {
      var newQty = existing.cantidad + 1;
      var updateResult = await getSupabase()
        .from('carrito')
        .update({ cantidad: newQty })
        .eq('id', existing.id);

      if (updateResult.error) throw updateResult.error;
      existing.cantidad = newQty;
    } else {
      var insertResult = await getSupabase()
        .from('carrito')
        .insert({ usuario_id: currentUser.id, producto_id: productoId, cantidad: 1 })
        .select('id');

      if (insertResult.error) throw insertResult.error;

      var producto = productosData.find(function (p) { return String(p.id) === String(productoId); });
      carritoItems.push({
        id: insertResult.data[0].id,
        producto_id: productoId,
        cantidad: 1,
        producto: producto || null,
      });
    }

    updateCartBadge();
    showToast('Agregado al carrito.', 'success');
  } catch (err) {
    console.error('Error al agregar al carrito:', err);
    var msg = 'Error al agregar producto.';
    if (err && err.code === 'PGRST116') msg = 'Verifica las políticas RLS de la tabla carrito.';
    if (err && err.code === '23503') msg = 'El producto ya no está disponible.';
    if (err && err.code === '42501') msg = 'RLS bloquea el carrito. Ejecuta la política SQL en Supabase.';
    showToast(msg, 'error');
  }
}

async function removeFromCart(cartItemId) {
  try {
    var result = await getSupabase().from('carrito').delete().eq('id', cartItemId);

    if (result.error) throw result.error;

    carritoItems = carritoItems.filter(function (item) { return item.id !== cartItemId; });
    updateCartBadge();
    renderCarrito();
    showToast('Producto eliminado del carrito.', 'info');
  } catch (err) {
    console.error('Error al eliminar del carrito:', err);
    var msg = 'Error al eliminar producto.';
    if (err && err.code === '42501') msg = 'RLS bloquea la operación. Ejecuta las políticas SQL.';
    showToast(msg, 'error');
  }
}

async function updateCartQuantity(cartItemId, nuevaCantidad) {
  if (nuevaCantidad < 1) {
    await removeFromCart(cartItemId);
    return;
  }

  try {
    var result = await getSupabase()
      .from('carrito')
      .update({ cantidad: nuevaCantidad })
      .eq('id', cartItemId);

    if (result.error) throw result.error;

    var item = carritoItems.find(function (i) { return i.id === cartItemId; });
    if (item) item.cantidad = nuevaCantidad;

    updateCartBadge();
    renderCarrito();
  } catch (err) {
    console.error('Error al actualizar cantidad:', err);
    var msg = 'Error al actualizar.';
    if (err && err.code === '42501') msg = 'RLS bloquea la operación. Ejecuta las políticas SQL.';
    showToast(msg, 'error');
  }
}

async function clearCart() {
  if (!currentUser) return;
  try {
    var result = await getSupabase().from('carrito').delete().eq('usuario_id', currentUser.id);
    if (result.error) throw result.error;
    carritoItems = [];
    updateCartBadge();
  } catch (err) {
    console.error('Error al vaciar carrito:', err);
  }
}

function getCartTotal() {
  return carritoItems.reduce(function (total, item) {
    if (!item.producto) return total;
    var precio = item.producto.precio_oferta || item.producto.precio_regular || 0;
    return total + precio * item.cantidad;
  }, 0);
}

function updateCartBadge() {
  var count = carritoItems.reduce(function (sum, item) { return sum + item.cantidad; }, 0);

  function setBadge(el, c) {
    if (!el) return;
    if (c > 0) {
      el.textContent = c > 99 ? '99+' : String(c);
      el.classList.remove('hidden');
      el.classList.add('pulse');
      setTimeout(function () { el.classList.remove('pulse'); }, 400);
    } else {
      el.classList.add('hidden');
    }
  }

  setBadge(document.getElementById('cart-badge'), count);
  setBadge(document.getElementById('mobile-cart-badge'), count);
}

// ============================================
// CHECKOUT
// ============================================
async function processCheckout() {
  if (!currentUser) {
    openAuthModal(null);
    showToast('Inicia sesión para pagar.', 'info');
    return;
  }

  if (carritoItems.length === 0) {
    showToast('Tu carrito está vacío.', 'info');
    return;
  }

  var btn = document.getElementById('btn-checkout');
  var total = getCartTotal();

  try {
    setButtonLoading(btn, true, 'Procesando pago...');

    var nombreCliente = ((perfilesData.nombre || '') + ' ' + (perfilesData.apellidos || '')).trim();
    if (!nombreCliente) {
      nombreCliente = currentUser.user_metadata.full_name || currentUser.email || 'Cliente online';
    }

    var descripcionOnline = carritoItems.map(function (item) {
      var nombre = item.producto ? item.producto.nombre : ('Producto #' + item.producto_id);
      return nombre + ' x' + item.cantidad;
    }).join(', ');

    var hoy = new Date();
    var fechaLocal = hoy.getFullYear() + '-' +
      String(hoy.getMonth() + 1).padStart(2, '0') + '-' +
      String(hoy.getDate()).padStart(2, '0');

    var movimientoResult = await getSupabase()
      .from('movimientos')
      .insert({
        cliente: nombreCliente,
        tipo: 'pedido',
        usuario_id: currentUser.id,
        monto: total,
        origen: 'online',
        estado: 'pagado',
        descripcion: descripcionOnline,
        fecha: fechaLocal,
      })
      .select('id')
      .single();

    if (movimientoResult.error) throw movimientoResult.error;

    var movimientoId = movimientoResult.data.id;

    var detalles = carritoItems.map(function (item) {
      var precio = item.producto.precio_oferta || item.producto.precio_regular || 0;
      return {
        movimiento_id: movimientoId,
        producto_id: item.producto_id,
        cantidad: item.cantidad,
        precio_unitario: precio,
      };
    });

    var detallesResult = await getSupabase().from('detalles_movimiento').insert(detalles);

    if (detallesResult.error) throw detallesResult.error;

    await clearCart();

    showToast('Pago exitoso. Gracias por tu compra.', 'success', 4000);
    carritoItems = [];
    updateCartBadge();
    renderCarrito();
    switchView('vista-inicio');
  } catch (err) {
    console.error('Checkout error:', err);
    var msg = 'Error al procesar el pago. Intenta de nuevo.';
    if (err && err.code === '42501') {
      if (/movimientos/i.test(err.message || '')) msg = 'RLS bloquea movimientos. Ejecuta la política SQL.';
      else if (/detalles/i.test(err.message || '')) msg = 'RLS bloquea detalles_movimiento. Ejecuta la política SQL.';
      else msg = 'RLS bloquea la operación. Ejecuta las políticas SQL.';
    }
    if (err && err.code === '23503') msg = 'Producto no encontrado en el catálogo.';
    showToast(msg, 'error');
  } finally {
    setButtonLoading(btn, false);
  }
}

// ============================================
// RENDERIZADO UI
// ============================================
function renderCatalogo() {
  var container = document.getElementById('catalogo-container');
  if (!container) return;

  var filtered = getFilteredProductos();
  var placeholder = getFotoPlaceholder();

  if (filtered.length === 0) {
    container.innerHTML =
      '<div class="col-span-full empty-state">' +
      '<span class="material-symbols-outlined">search_off</span>' +
      '<p class="text-[#94A3B8] font-medium">No se encontraron productos en esta categoría.</p>' +
      '</div>';
    return;
  }

  container.innerHTML = filtered.map(function (producto, index) {
    var imgUrl = getFotoProducto(producto.codigo);
    var onerrorFn = buildImgOnError(producto.codigo);
    var cat = escapeHtml(producto.categoria || 'General');
    var nombre = escapeHtml(producto.nombre);
    var precioReg = formatMoney(producto.precio_regular);
    var precioOferta = formatMoney(producto.precio_oferta);
    var condicion = escapeHtml(producto.condicion || '');

    return (
      '<div class="producto-card group scroll-reveal transition-all duration-300" data-delay="' + (index * 60) + '">' +
        '<div class="aspect-[4/3] overflow-hidden bg-[#F1F5F9]">' +
          '<img src="' + imgUrl + '" alt="' + nombre + '" class="img-zoom" loading="lazy" onerror="' + onerrorFn + '">' +
        '</div>' +
        '<div class="p-4">' +
          '<span class="categoria-label">' + cat + '</span>' +
          '<h3 class="font-semibold text-[.9375rem] text-[#1E293B] mt-1 leading-snug line-clamp-2">' + nombre + '</h3>' +
          '<div class="flex items-baseline gap-2 mt-3">' +
            '<span class="precio-oferta">' + precioOferta + '</span>' +
            '<span class="precio-tachado">' + precioReg + '</span>' +
          '</div>' +
          '<div class="flex items-center justify-between mt-2">' +
            (condicion ? '<span class="condicion-chip">' + condicion + '</span>' : '<span></span>') +
            '<button class="add-btn transition-transform duration-200 hover:scale-110 active:scale-95" data-producto-id="' + producto.id + '" title="Agregar al carrito" aria-label="Agregar ' + nombre + ' al carrito">' +
              '<span class="material-symbols-outlined">add_shopping_cart</span>' +
            '</button>' +
          '</div>' +
        '</div>' +
      '</div>'
    );
  }).join('');

  initScrollReveal();
}

function renderCarrito() {
  var container = document.getElementById('cart-items-container');
  var summary = document.getElementById('cart-summary');
  var subtitle = document.getElementById('cart-subtitle');

  if (!container) return;

  if (!currentUser) {
    container.innerHTML =
      '<div class="empty-state">' +
      '<span class="material-symbols-outlined">shopping_cart</span>' +
      '<p class="text-[#64748B] font-medium mb-1">Inicia sesión para ver tu carrito</p>' +
      '<p class="text-[#94A3B8] text-[.875rem] mb-4">Guarda tus productos y recibe ofertas personalizadas.</p>' +
      '<button class="btn-brand h-11 px-6 text-[.875rem]" id="btn-login-from-cart">' +
      '<span class="material-symbols-outlined" style="font-size:18px">login</span> Iniciar Sesión' +
      '</button>' +
      '</div>';
    if (summary) summary.style.display = 'none';
    if (subtitle) subtitle.textContent = 'Inicia sesión para administrar tu carrito.';
    return;
  }

  if (carritoItems.length === 0) {
    container.innerHTML =
      '<div class="empty-state">' +
      '<span class="material-symbols-outlined">inventory_2</span>' +
      '<p class="text-[#64748B] font-medium mb-1">Tu carrito está vacío</p>' +
      '<p class="text-[#94A3B8] text-[.875rem] mb-4">Agrega productos desde el catálogo.</p>' +
      '<button class="btn-brand h-11 px-6 text-[.875rem]" data-view="vista-catalogo">' +
      '<span class="material-symbols-outlined" style="font-size:18px">explore</span> Ir al catálogo' +
      '</button>' +
      '</div>';
    if (summary) summary.style.display = 'none';
    if (subtitle) subtitle.textContent = 'Agrega productos desde nuestro catálogo.';
    return;
  }

  if (subtitle) subtitle.textContent = carritoItems.length + ' producto' + (carritoItems.length !== 1 ? 's' : '') + ' en tu carrito.';

  container.innerHTML = carritoItems.map(function (item) {
    var p = item.producto;
    var imgUrl = p ? getFotoProducto(p.codigo) : getFotoPlaceholder();
    var onerrorFn = p ? buildImgOnError(p.codigo) : '';
    var nombre = p ? escapeHtml(p.nombre) : 'Producto no disponible';
    var precio = p ? (p.precio_oferta || p.precio_regular || 0) : 0;
    var subtotal = precio * item.cantidad;

    return (
      '<div class="cart-item">' +
        '<img src="' + imgUrl + '" alt="' + nombre + '" class="cart-item-img" loading="lazy" onerror="' + onerrorFn + '">' +
        '<div class="flex-1 min-w-0">' +
          '<h4 class="font-semibold text-[.875rem] text-[#1E293B] truncate">' + nombre + '</h4>' +
          '<p class="text-[#64748B] text-[.8125rem]">' + formatMoney(precio) + ' c/u</p>' +
          '<div class="flex items-center gap-2 mt-2">' +
            '<button class="cart-qty-btn" data-action="decrease" data-item-id="' + item.id + '" data-current-qty="' + item.cantidad + '">-</button>' +
            '<span class="font-semibold text-[.9375rem] min-w-[28px] text-center">' + item.cantidad + '</span>' +
            '<button class="cart-qty-btn" data-action="increase" data-item-id="' + item.id + '" data-current-qty="' + item.cantidad + '">+</button>' +
          '</div>' +
        '</div>' +
        '<div class="text-right flex flex-col items-end gap-2">' +
          '<span class="font-bold text-[1.0625rem] text-[#1E293B]">' + formatMoney(subtotal) + '</span>' +
          '<button class="cart-remove-btn" data-action="remove" data-item-id="' + item.id + '" title="Eliminar" aria-label="Eliminar ' + nombre + '">' +
            '<span class="material-symbols-outlined" style="font-size:20px">delete</span>' +
          '</button>' +
        '</div>' +
      '</div>'
    );
  }).join('');

  var total = getCartTotal();
  var totalEl = document.getElementById('cart-total');
  if (totalEl) totalEl.textContent = formatMoney(total);

  if (summary) summary.style.display = 'block';
}

function updateNavbar() {
  var btnLabel = document.getElementById('btn-auth-label');
  var btnDesktop = document.getElementById('btn-auth-desktop');
  var navMiCuenta = document.getElementById('nav-mi-cuenta');
  var mobileNavPerfil = document.getElementById('mobile-nav-perfil');
  var btnMobileLogin = document.getElementById('btn-mobile-login');
  var btnMobileLogout = document.getElementById('btn-mobile-logout');

  if (currentUser) {
    if (btnLabel) {
      var name = (currentUser.user_metadata && currentUser.user_metadata.full_name) || currentUser.email || 'Mi Cuenta';
      btnLabel.textContent = name.length > 18 ? name.substring(0, 16) + '...' : name;
    }
    if (btnDesktop) btnDesktop.classList.add('logged-in');
    if (navMiCuenta) navMiCuenta.classList.remove('hidden');
    if (mobileNavPerfil) mobileNavPerfil.classList.remove('hidden');
    if (btnMobileLogin) btnMobileLogin.style.display = 'none';
    if (btnMobileLogout) btnMobileLogout.style.display = 'flex';
  } else {
    if (btnLabel) btnLabel.textContent = 'Iniciar Sesión';
    if (btnDesktop) btnDesktop.classList.remove('logged-in');
    if (navMiCuenta) navMiCuenta.classList.add('hidden');
    if (mobileNavPerfil) mobileNavPerfil.classList.add('hidden');
    if (btnMobileLogin) btnMobileLogin.style.display = 'flex';
    if (btnMobileLogout) btnMobileLogout.style.display = 'none';
  }

  updateCartBadge();
}

function updateMobileCartBadge() {
  var badge = document.getElementById('mobile-cart-badge');
  if (!badge) return;
  var count = carritoItems.reduce(function (sum, item) { return sum + item.cantidad; }, 0);
  if (count > 0) {
    badge.textContent = count > 99 ? '99+' : String(count);
    badge.classList.remove('hidden');
  } else {
    badge.classList.add('hidden');
  }
}

function openMobileDrawer() {
  var overlay = document.getElementById('mobile-drawer-overlay');
  var drawer = document.getElementById('mobile-drawer');
  if (!overlay || !drawer) return;
  overlay.classList.remove('hidden');
  requestAnimationFrame(function () {
    overlay.classList.add('show');
    drawer.classList.add('open');
  });
  document.body.style.overflow = 'hidden';
}

function closeMobileDrawer() {
  var overlay = document.getElementById('mobile-drawer-overlay');
  var drawer = document.getElementById('mobile-drawer');
  if (!overlay || !drawer) return;
  overlay.classList.remove('show');
  drawer.classList.remove('open');
  setTimeout(function () {
    overlay.classList.add('hidden');
    document.body.style.overflow = '';
  }, 350);
}

function updateMobileDrawerActive(viewId) {
  document.querySelectorAll('.mobile-nav-item').forEach(function (item) {
    if (item.dataset.view === viewId) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });
}

function initStripe() {
  if (!window.Stripe) {
    console.warn('Stripe.js no se cargó. El pago funcionará sin tarjeta real.');
    return;
  }
  stripeInstance = window.Stripe(STRIPE_PUBLISHABLE_KEY, { locale: 'es' });
}

function openPagoModal() {
  var overlay = document.getElementById('pago-overlay');
  if (!overlay) return;
  var total = getCartTotal();
  var totalDisplay = document.getElementById('pago-total-display');
  if (totalDisplay) totalDisplay.textContent = formatMoney(total);

  document.getElementById('pago-holder').value = '';
  document.getElementById('pago-error').classList.remove('show');
  document.getElementById('pago-error').textContent = '';
  document.getElementById('stripe-card-errors').classList.remove('show');
  document.getElementById('stripe-card-errors').textContent = '';
  document.getElementById('pago-card-number').textContent = '•••• •••• •••• ••••';
  document.getElementById('pago-card-brand').textContent = '●●●●';
  document.getElementById('pago-card-holder').textContent = '—';
  document.getElementById('pago-card-preview').className = 'pago-card-preview mb-5';
  var submitBtn = document.getElementById('btn-pago-submit');
  if (submitBtn) { submitBtn.disabled = true; setButtonLoading(submitBtn, false); }

  overlay.classList.remove('hidden');
  requestAnimationFrame(function () {
    overlay.classList.add('show');
  });
  document.body.style.overflow = 'hidden';

  mountStripeCard();
}

function closePagoModal() {
  var overlay = document.getElementById('pago-overlay');
  if (!overlay) return;
  overlay.classList.remove('show');
  unmountStripeCard();
  setTimeout(function () {
    overlay.classList.add('hidden');
    document.body.style.overflow = '';
  }, 300);
}

function mountStripeCard() {
  if (!stripeInstance) {
    document.getElementById('adblock-warning').classList.add('show');
    return;
  }

  if (cardElement) { unmountStripeCard(); }

  document.getElementById('adblock-warning').classList.remove('show');

  var elements = stripeInstance.elements({ locale: 'es' });
  cardElement = elements.create('card', {
    style: {
      base: {
        fontFamily: '"Hanken Grotesk", system-ui, sans-serif',
        fontSize: '15px',
        color: '#1E293B',
        '::placeholder': { color: '#94A3B8' },
      },
      invalid: { color: '#DC2626', iconColor: '#DC2626' },
    },
    hidePostalCode: true,
  });

  cardElement.mount('#stripe-card-element');

  cardElement.on('change', function (event) {
    var displayError = document.getElementById('stripe-card-errors');
    if (event.error) {
      displayError.textContent = event.error.message;
      displayError.classList.add('show');
    } else {
      displayError.classList.remove('show');
      displayError.textContent = '';
    }

    var submitBtn = document.getElementById('btn-pago-submit');
    if (submitBtn) submitBtn.disabled = !event.complete;

    if (event.brand && event.brand !== 'unknown') {
      var preview = document.getElementById('pago-card-preview');
      var brandEl = document.getElementById('pago-card-brand');
      if (brandEl) brandEl.textContent = event.brand.toUpperCase();
      if (preview) {
        preview.className = 'pago-card-preview mb-5' +
          (event.brand === 'visa' ? ' is-visa' : '') +
          (event.brand === 'mastercard' ? ' is-mc' : '');
      }
    }
  });

  cardElement.on('ready', function () {
    var submitBtn = document.getElementById('btn-pago-submit');
    if (submitBtn) submitBtn.disabled = true;
  });
}

function unmountStripeCard() {
  if (cardElement) {
    cardElement.unmount();
    cardElement.destroy();
    cardElement = null;
  }
}

var pagoHolderInput = null;
function setupPagoHolderListener() {
  pagoHolderInput = document.getElementById('pago-holder');
  if (!pagoHolderInput) return;
  pagoHolderInput.addEventListener('input', function () {
    var preview = document.getElementById('pago-card-holder');
    if (preview) preview.textContent = this.value.trim() || '—';
  });
}

async function stripeCheckout() {
  var errorEl = document.getElementById('pago-error');
  var submitBtn = document.getElementById('btn-pago-submit');
  var holder = (document.getElementById('pago-holder').value || '').trim();

  if (!holder || holder.length < 3) {
    if (errorEl) { errorEl.textContent = 'Ingresa el nombre del titular.'; errorEl.classList.add('show'); }
    return;
  }

  if (!stripeInstance || !cardElement) {
    // Fallback sin Stripe: pago directo
    if (errorEl) errorEl.classList.remove('show');
    closePagoModal();
    processCheckout();
    return;
  }

  try {
    setButtonLoading(submitBtn, true, 'Procesando...');
    if (errorEl) errorEl.classList.remove('show');

    var totalCentavos = Math.round(getCartTotal() * 100);

    // 1. Crear PaymentIntent via Edge Function
    var intentRes = await fetch(STRIPE_EDGE_FUNCTION, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + SUPABASE_KEY,
      },
      body: JSON.stringify({ amount: totalCentavos, descripcion: 'Compra BetterMancera' }),
    });

    if (!intentRes.ok) {
      var intentErr = await intentRes.json().catch(function () { return {}; });
      console.warn('Edge function falló, usando pago directo:', intentErr);
      closePagoModal();
      processCheckout();
      return;
    }

    var intentData = await intentRes.json();
    if (!intentData.clientSecret) {
      closePagoModal();
      processCheckout();
      return;
    }

    // 2. Confirmar pago con Stripe
    var stripeResult = await stripeInstance.confirmCardPayment(intentData.clientSecret, {
      payment_method: {
        card: cardElement,
        billing_details: { name: holder },
      },
    });

    if (stripeResult.error) {
      if (errorEl) { errorEl.textContent = stripeResult.error.message; errorEl.classList.add('show'); }
      return;
    }

    if (stripeResult.paymentIntent && stripeResult.paymentIntent.status === 'succeeded') {
      closePagoModal();
      processCheckout();
    } else {
      if (errorEl) { errorEl.textContent = 'El pago requiere verificación adicional. Intenta de nuevo.'; errorEl.classList.add('show'); }
    }
  } catch (err) {
    console.error('Stripe checkout error:', err);
    closePagoModal();
    processCheckout();
  } finally {
    setButtonLoading(submitBtn, false);
  }
}

// ============================================
// CATEGORÍA CHIPS
// ============================================
function renderCategoriaChips() {
  var container = document.getElementById('chips-categorias');
  if (!container) return;

  var categorias = getCategoriasUnicas();
  var chips = categorias.map(function (cat) {
    var activeClass = cat === categoriaActiva ? ' active' : '';
    return '<button class="chip-categoria' + activeClass + '" data-cat="' + escapeHtml(cat) + '">' + escapeHtml(cat) + '</button>';
  });

  container.innerHTML =
    '<button class="chip-categoria' + (categoriaActiva === 'todas' ? ' active' : '') + '" data-cat="todas">Todas</button>' +
    chips.join('');
}

// ============================================
// NAVEGACIÓN
// ============================================
function switchView(viewId) {
  currentView = viewId;

  document.querySelectorAll('.view-section').forEach(function (section) {
    section.classList.remove('active');
    if (section.id === viewId) {
      section.classList.add('active');
    }
  });

  document.querySelectorAll('.nav-link').forEach(function (link) {
    if (link.dataset.view === viewId) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });

  updateMobileDrawerActive(viewId);
  closeMobileDrawer();

  window.scrollTo({ top: 0, behavior: 'smooth' });

  if (viewId === 'vista-catalogo') {
    renderCategoriaChips();
    if (productosData.length === 0) {
      cargarCatalogo();
    } else {
      renderCatalogo();
    }
  }

  if (viewId === 'vista-carrito') {
    renderCarrito();
  }

  if (viewId === 'vista-inicio') {
    initScrollReveal();
  }

  if (viewId === 'vista-perfil') {
    cargarPerfil().then(function () {
      return cargarHistorialPedidos();
    }).then(function () {
      renderPerfil();
    });
  }
}

// ============================================
// SCROLL REVEAL (IntersectionObserver)
// ============================================
function initScrollReveal() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.querySelectorAll('.scroll-reveal').forEach(function (el) {
      el.classList.add('revealed');
    });
    return;
  }

  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var delay = parseInt(entry.target.dataset.delay) || 0;
          setTimeout(function () {
            entry.target.classList.add('revealed');
          }, delay);
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.08, rootMargin: '0px 0px -30px 0px' }
  );

  document.querySelectorAll('.scroll-reveal:not(.revealed)').forEach(function (el) {
    observer.observe(el);
  });
}

// ============================================
// HERO BACKGROUND CAROUSEL (crossfade)
// ============================================
let heroCarouselIndex = 0;
let heroCarouselTimer = null;

function initHeroCarousel() {
  var layers = document.querySelectorAll('.hero-bg-layer');
  var dots = document.querySelectorAll('.hero-dot');
  if (!layers.length) return;

  function showSlide(index) {
    layers.forEach(function (l, i) { l.classList.toggle('active', i === index); });
    dots.forEach(function (d, i) { d.classList.toggle('active', i === index); });
    heroCarouselIndex = index;
  }

  function nextSlide() {
    showSlide((heroCarouselIndex + 1) % layers.length);
  }

  function startTimer() {
    stopTimer();
    heroCarouselTimer = setInterval(nextSlide, 4000);
  }

  function stopTimer() {
    if (heroCarouselTimer) { clearInterval(heroCarouselTimer); heroCarouselTimer = null; }
  }

  dots.forEach(function (dot) {
    dot.addEventListener('click', function () {
      showSlide(parseInt(dot.dataset.index));
      stopTimer();
      startTimer();
    });
  });

  var heroEl = document.getElementById('hero-fullscreen');
  if (heroEl) {
    heroEl.addEventListener('mouseenter', stopTimer);
    heroEl.addEventListener('mouseleave', startTimer);
    heroEl.addEventListener('touchstart', stopTimer, { passive: true });
    heroEl.addEventListener('touchend', function () { stopTimer(); startTimer(); });
  }

  showSlide(0);
  startTimer();
}

// ============================================
// EVENT LISTENERS
// ============================================
function initEventListeners() {
  // Navegación por navbar
  document.querySelectorAll('.nav-link').forEach(function (link) {
    link.addEventListener('click', function () {
      switchView(link.dataset.view);
    });
  });

  // Botones con data-view (CTAs, etc.)
  document.body.addEventListener('click', function (event) {
    var btn = event.target.closest('[data-view]');
    if (!btn) return;
    if (btn.closest('.nav-link')) return;
    if (btn.closest('#btn-cart')) {
      switchView('vista-carrito');
      return;
    }
    switchView(btn.dataset.view);
  });

  // Ícono de carrito en navbar
  var btnCart = document.getElementById('btn-cart');
  if (btnCart) {
    btnCart.addEventListener('click', function () {
      switchView('vista-carrito');
    });
  }

  // Auth modal: abrir (o ir a perfil si ya hay sesión)
  document.body.addEventListener('click', function (event) {
    var btn = event.target.closest('#btn-auth-desktop, #btn-auth-mobile, #btn-login-from-cart');
    if (!btn) return;

    if (currentUser) {
      switchView('vista-perfil');
    } else {
      openAuthModal(null);
    }
  });

  // Auth modal: cerrar
  var btnAuthClose = document.getElementById('btn-auth-close');
  if (btnAuthClose) {
    btnAuthClose.addEventListener('click', closeAuthModal);
  }

  var authOverlay = document.getElementById('auth-overlay');
  if (authOverlay) {
    authOverlay.addEventListener('click', function (e) {
      if (e.target === authOverlay) closeAuthModal();
    });
  }

  // Auth modal: tabs
  document.getElementById('auth-tabs').addEventListener('click', function (e) {
    var tab = e.target.closest('.auth-tab');
    if (!tab) return;

    document.querySelectorAll('.auth-tab').forEach(function (t) { t.classList.remove('active'); });
    tab.classList.add('active');

    var formLogin = document.getElementById('form-login');
    var formRegister = document.getElementById('form-register');

    if (tab.dataset.tab === 'register') {
      formLogin.classList.add('hidden');
      formRegister.classList.remove('hidden');
    } else {
      formLogin.classList.remove('hidden');
      formRegister.classList.add('hidden');
    }
  });

  // Auth modal: login submit
  document.getElementById('form-login').addEventListener('submit', function (e) {
    e.preventDefault();
    var email = document.getElementById('login-email').value.trim();
    var password = document.getElementById('login-password').value;
    if (!email || !password) {
      var errorEl = document.getElementById('login-error');
      if (errorEl) { errorEl.textContent = 'Completa todos los campos.'; errorEl.classList.add('show'); }
      return;
    }
    loginUser(email, password);
  });

  // Auth modal: register submit
  document.getElementById('form-register').addEventListener('submit', function (e) {
    e.preventDefault();
    var nombre = document.getElementById('reg-nombre').value.trim();
    var apellidos = document.getElementById('reg-apellidos').value.trim();
    var telefono = document.getElementById('reg-telefono').value.trim();
    var ciudad = document.getElementById('reg-ciudad').value;
    var email = document.getElementById('reg-email').value.trim();
    var password = document.getElementById('reg-password').value;

    if (!nombre || !apellidos || !email || !password) {
      var errorEl = document.getElementById('register-error');
      if (errorEl) { errorEl.textContent = 'Completa todos los campos obligatorios.'; errorEl.classList.add('show'); }
      return;
    }
    if (!ciudad) {
      var errorEl = document.getElementById('register-error');
      if (errorEl) { errorEl.textContent = 'Selecciona tu ciudad para continuar.'; errorEl.classList.add('show'); }
      return;
    }
    if (password.length < 8) {
      var errorEl = document.getElementById('register-error');
      if (errorEl) { errorEl.textContent = 'La contraseña debe tener al menos 8 caracteres.'; errorEl.classList.add('show'); }
      return;
    }
    registerUser(nombre, apellidos, telefono, ciudad, email, password);
  });

  // Catálogo: chips de categoría
  var chipsContainer = document.getElementById('chips-categorias');
  if (chipsContainer) {
    chipsContainer.addEventListener('click', function (e) {
      var chip = e.target.closest('.chip-categoria');
      if (!chip) return;

      document.querySelectorAll('#chips-categorias .chip-categoria').forEach(function (c) { c.classList.remove('active'); });
      chip.classList.add('active');
      categoriaActiva = chip.dataset.cat;
      renderCatalogo();
    });
  }

  // Catálogo: agregar al carrito
  var catalogoContainer = document.getElementById('catalogo-container');
  if (catalogoContainer) {
    catalogoContainer.addEventListener('click', function (e) {
      var addBtn = e.target.closest('.add-btn');
      if (!addBtn) return;

      var rawId = addBtn.dataset.productoId;
      if (!rawId) return;
      var productoId = /^\d+$/.test(rawId) ? parseInt(rawId, 10) : rawId;

      addBtn.style.transform = 'scale(1.15)';
      setTimeout(function () { addBtn.style.transform = ''; }, 200);

      addToCart(productoId);
    });
  }

  // Carrito: acciones (quitar, cambiar cantidad)
  var cartContainer = document.getElementById('cart-items-container');
  if (cartContainer) {
    cartContainer.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-action]');
      if (!btn) return;

      var rawId = btn.dataset.itemId;
      if (!rawId) return;
      var itemId = /^\d+$/.test(rawId) ? parseInt(rawId, 10) : rawId;

      if (btn.dataset.action === 'remove') {
        removeFromCart(itemId);
      } else if (btn.dataset.action === 'increase') {
        var currentQty = parseInt(btn.dataset.currentQty) || 0;
        updateCartQuantity(itemId, currentQty + 1);
      } else if (btn.dataset.action === 'decrease') {
        var currentQty = parseInt(btn.dataset.currentQty) || 1;
        updateCartQuantity(itemId, currentQty - 1);
      }
    });
  }

  // Checkout → abre modal de pago
  var btnCheckout = document.getElementById('btn-checkout');
  if (btnCheckout) {
    btnCheckout.addEventListener('click', function () {
      if (!currentUser) {
        openAuthModal(null);
        showToast('Inicia sesión para pagar.', 'info');
        return;
      }
      if (carritoItems.length === 0) {
        showToast('Tu carrito está vacío.', 'info');
        return;
      }
      openPagoModal();
    });
  }

  // Perfil: cerrar sesión
  var btnLogoutProfile = document.getElementById('btn-logout-profile');
  if (btnLogoutProfile) {
    btnLogoutProfile.addEventListener('click', function () {
      if (confirm('¿Cerrar sesión?')) logoutUser();
    });
  }

  // Perfil: login from empty state
  document.body.addEventListener('click', function (event) {
    var btn = event.target.closest('#btn-login-from-profile');
    if (!btn) return;
    openAuthModal(null);
  });

  // Perfil: toggle detalle de pedido
  var histContainer = document.getElementById('historial-pedidos-container');
  if (histContainer) {
    histContainer.addEventListener('click', function (e) {
      var card = e.target.closest('.pedido-card');
      if (!card) return;
      var pedidoId = parseInt(card.dataset.pedidoId);
      if (isNaN(pedidoId)) return;
      togglePedidoDetalle(pedidoId);
    });
  }

  // Mobile drawer: abrir
  var btnHamburger = document.getElementById('btn-hamburger');
  if (btnHamburger) {
    btnHamburger.addEventListener('click', openMobileDrawer);
  }

  // Mobile drawer: cerrar
  var btnDrawerClose = document.getElementById('btn-drawer-close');
  if (btnDrawerClose) {
    btnDrawerClose.addEventListener('click', closeMobileDrawer);
  }

  var drawerOverlay = document.getElementById('mobile-drawer-overlay');
  if (drawerOverlay) {
    drawerOverlay.addEventListener('click', closeMobileDrawer);
  }

  // Mobile drawer: navegación
  document.getElementById('mobile-drawer').addEventListener('click', function (e) {
    var item = e.target.closest('.mobile-nav-item');
    if (!item || !item.dataset.view) return;
    switchView(item.dataset.view);
  });

  // Mobile drawer: login/logout
  var btnMobileLogout = document.getElementById('btn-mobile-logout');
  if (btnMobileLogout) {
    btnMobileLogout.addEventListener('click', function () {
      if (confirm('¿Cerrar sesión?')) logoutUser();
    });
  }

  var btnMobileLogin = document.getElementById('btn-mobile-login');
  if (btnMobileLogin) {
    btnMobileLogin.addEventListener('click', function () {
      closeMobileDrawer();
      openAuthModal(null);
    });
  }

  // Payment modal: cerrar
  var btnPagoClose = document.getElementById('btn-pago-close');
  if (btnPagoClose) {
    btnPagoClose.addEventListener('click', closePagoModal);
  }

  var pagoOverlay = document.getElementById('pago-overlay');
  if (pagoOverlay) {
    pagoOverlay.addEventListener('click', function (e) {
      if (e.target === pagoOverlay) closePagoModal();
    });
  }

  setupPagoHolderListener();

  // Payment modal: form submit (Stripe)
  document.getElementById('form-pago').addEventListener('submit', function (e) {
    e.preventDefault();
    stripeCheckout();
  });

  // Tecla Escape cierra modales
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      var authOverlay = document.getElementById('auth-overlay');
      if (authOverlay && !authOverlay.classList.contains('hidden')) {
        closeAuthModal();
        return;
      }
      var pagoOv = document.getElementById('pago-overlay');
      if (pagoOv && !pagoOv.classList.contains('hidden')) {
        closePagoModal();
        return;
      }
      var drawerOv = document.getElementById('mobile-drawer-overlay');
      if (drawerOv && !drawerOv.classList.contains('hidden')) {
        closeMobileDrawer();
        return;
      }
    }
  });
}

// ============================================
// INICIO DE LA APLICACIÓN
// ============================================
async function init() {
  try {
    getSupabase();
  } catch (err) {
    console.error('Error al inicializar Supabase:', err);
    showToast('Error de conexión. Recarga la página.', 'error');
    return;
  }

  initAuth();
  initStripe();
  initEventListeners();
  await cargarCatalogo();
  renderCategoriaChips();
  initScrollReveal();
  initHeroCarousel();
}

document.addEventListener('DOMContentLoaded', init);
