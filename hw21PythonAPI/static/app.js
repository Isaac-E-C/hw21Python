const API = '/sersalud/appointments';

let doctorsCache = [];
let therapiesCache = [];

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.nav-links a').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      navigateTo(link.dataset.section);
    });
  });

  document.getElementById('has-exams').addEventListener('change', function () {
    document.getElementById('exams-group').style.display = this.checked ? 'block' : 'none';
  });

  document.getElementById('appointment-date').addEventListener('change', fetchAvailableSlots);
  document.getElementById('doctor-select').addEventListener('change', fetchAvailableSlots);

  loadDashboard();
  loadDoctorTherapyData();
});

function navigateTo(section) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-links a').forEach(a => a.classList.remove('active'));
  document.getElementById(section).classList.add('active');
  const link = document.querySelector(`.nav-links a[data-section="${section}"]`);
  if (link) link.classList.add('active');

  if (section === 'dashboard') loadDashboard();
  if (section === 'appointments') loadAppointments();
  if (section === 'create') loadDoctorTherapyData();
}

async function apiCall(method, path, body) {
  try {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(API + path, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  } catch (err) {
    showToast(err.message, 'error');
    throw err;
  }
}

async function loadDashboard() {
  try {
    const appointments = await apiCall('GET', '/');
    document.getElementById('stat-total').textContent = appointments.length;
    document.getElementById('stat-pending').textContent = appointments.filter(a => a.status === 'pending').length;
    document.getElementById('stat-confirmed').textContent = appointments.filter(a => a.status === 'confirmed').length;
    document.getElementById('stat-completed').textContent = appointments.filter(a => a.status === 'completed').length;
    document.getElementById('stat-cancelled').textContent = appointments.filter(a => a.status === 'cancelled').length;
  } catch {
    document.getElementById('stat-total').textContent = '—';
  }
}

async function loadDoctorTherapyData() {
  try {
    const appointments = await apiCall('GET', '/');
    const doctorsMap = new Map();
    const therapiesMap = new Map();

    appointments.forEach(a => {
      if (a.doctor && a.doctor.id) {
        doctorsMap.set(a.doctor.id, a.doctor);
      }
      if (a.therapy && a.therapy.id) {
        therapiesMap.set(a.therapy.id, a.therapy);
      }
    });

    doctorsCache = Array.from(doctorsMap.values());
    therapiesCache = Array.from(therapiesMap.values());

    populateSelect('doctor-select', doctorsCache, 'fullName');
    populateSelect('therapy-select', therapiesCache, 'name');
  } catch {
    // data not available
  }
}

function populateSelect(id, items, labelKey) {
  const sel = document.getElementById(id);
  const current = sel.value;
  sel.innerHTML = '<option value="">Seleccione...</option>';
  items.forEach(item => {
    const opt = document.createElement('option');
    opt.value = item.id;
    opt.textContent = item[labelKey] || item.id;
    sel.appendChild(opt);
  });
  if (current) sel.value = current;
}

async function loadAppointments() {
  const container = document.getElementById('appointments-list');
  container.innerHTML = '<div class="empty-state">Cargando...</div>';

  const params = new URLSearchParams();
  const status = document.getElementById('filter-status').value.trim();
  const date = document.getElementById('filter-date').value;
  const patient = document.getElementById('filter-patient').value.trim();
  const doctor = document.getElementById('filter-doctor').value.trim();

  if (status) params.set('status', status);
  if (date) params.set('date', date);
  if (patient) params.set('patient_id', patient);
  if (doctor) params.set('doctor_id', doctor);

  const qs = params.toString();
  try {
    const appointments = await apiCall('GET', '/' + (qs ? '?' + qs : ''));
    if (appointments.length === 0) {
      container.innerHTML = '<div class="empty-state">No se encontraron citas. Use "Poblar Base de Datos" si est\u00e1 vac\u00edo.</div>';
      return;
    }
    container.innerHTML = '';
    appointments.forEach(a => {
      const card = document.createElement('div');
      card.className = 'appointment-card';
      card.innerHTML = `
        <div class="appointment-info">
          <h3>${escapeHtml(a.patient?.fullName || 'Paciente #' + a.patientId)}</h3>
          <p>${escapeHtml(a.doctor?.fullName || 'Dr. #' + a.doctorId)} &middot; ${escapeHtml(a.therapy?.name || 'Terapia')} &middot; ${a.date} ${a.time}</p>
        </div>
        <span class="appointment-status status-${a.status}">${a.status}</span>
      `;
      card.addEventListener('click', () => showDetail(a.id));
      container.appendChild(card);
    });
  } catch (err) {
    container.innerHTML = `<div class="empty-state">Error al cargar citas: ${err.message}</div>`;
  }
}

function clearFilters() {
  document.getElementById('filter-status').value = '';
  document.getElementById('filter-date').value = '';
  document.getElementById('filter-patient').value = '';
  document.getElementById('filter-doctor').value = '';
  loadAppointments();
}

async function showDetail(id) {
  try {
    const a = await apiCall('GET', '/' + id);
    const content = document.getElementById('detail-content');
    content.innerHTML = `
      <div class="card">
        <div class="detail-grid">
          <div class="detail-item">
            <label>Paciente</label>
            <span>${escapeHtml(a.patient?.fullName || 'N/A')}</span>
          </div>
          <div class="detail-item">
            <label>Doctor</label>
            <span>${escapeHtml(a.doctor?.fullName || 'N/A')}</span>
          </div>
          <div class="detail-item">
            <label>Especialidad</label>
            <span>${escapeHtml(a.doctor?.specialty || 'N/A')}</span>
          </div>
          <div class="detail-item">
            <label>Terapia</label>
            <span>${escapeHtml(a.therapy?.name || 'N/A')}</span>
          </div>
          <div class="detail-item">
            <label>Fecha</label>
            <span>${a.date}</span>
          </div>
          <div class="detail-item">
            <label>Hora</label>
            <span>${a.time}</span>
          </div>
          <div class="detail-item">
            <label>Estado</label>
            <span class="appointment-status status-${a.status}">${a.status}</span>
          </div>
          <div class="detail-item">
            <label>Duración</label>
            <span>${a.therapy?.duration || '—'} min</span>
          </div>
          <div class="detail-item">
            <label>Precio</label>
            <span>$${a.therapy?.price?.toFixed(2) || '—'}</span>
          </div>
          <div class="detail-item">
            <label>Seguro</label>
            <span>${escapeHtml(a.patient?.insuranceType || 'N/A')}</span>
          </div>
        </div>
        <div class="detail-item" style="margin-top:8px">
          <label>Síntomas</label>
          <p style="margin-top:4px;color:#4a5568">${escapeHtml(a.symptoms)}</p>
        </div>
        ${a.doctorNotes ? `
        <div class="detail-item" style="margin-top:8px">
          <label>Notas del Doctor</label>
          <p style="margin-top:4px;color:#4a5568">${escapeHtml(a.doctorNotes)}</p>
        </div>` : ''}
        ${a.cancellationReason ? `
        <div class="detail-item" style="margin-top:8px">
          <label>Motivo de Cancelación</label>
          <p style="margin-top:4px;color:#e53e3e">${escapeHtml(a.cancellationReason)}</p>
        </div>` : ''}
        <div class="detail-actions">
          <button class="btn btn-primary" onclick="navigateToEdit('${a.id}')">Actualizar</button>
          ${a.status === 'pending' || a.status === 'confirmed' ? `<button class="btn btn-danger" onclick="openCancelModal('${a.id}')">Cancelar</button>` : ''}
        </div>
      </div>
    `;
    navigateTo('detail');
  } catch {
    showToast('Error al cargar detalle', 'error');
  }
}

function navigateToEdit(id) {
  navigateTo('edit');
  document.getElementById('edit-id').value = id;
  document.getElementById('edit-status').value = '';
  document.getElementById('edit-doctor-notes').value = '';
}

async function updateAppointment(e) {
  e.preventDefault();
  const id = document.getElementById('edit-id').value;
  const body = {};
  const status = document.getElementById('edit-status').value;
  const notes = document.getElementById('edit-doctor-notes').value.trim();
  if (status) body.status = status;
  if (notes) body.doctorNotes = notes;
  if (!status && !notes) {
    showToast('Seleccione al menos un campo para actualizar', 'error');
    return;
  }
  try {
    await apiCall('PUT', '/' + id, body);
    showToast('Cita actualizada exitosamente', 'success');
    navigateTo('appointments');
    loadAppointments();
  } catch {
    showToast('Error al actualizar cita', 'error');
  }
}

function openCancelModal(id) {
  document.getElementById('cancel-id').value = id;
  document.getElementById('cancel-reason').value = '';
  document.getElementById('modal').style.display = 'flex';
}

function closeModal() {
  document.getElementById('modal').style.display = 'none';
}

async function confirmCancel() {
  const id = document.getElementById('cancel-id').value;
  const reason = document.getElementById('cancel-reason').value.trim();
  if (!reason) {
    showToast('Debe proporcionar un motivo de cancelación', 'error');
    return;
  }
  try {
    const res = await fetch(API + '/' + id, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Error al cancelar');
    showToast('Cita cancelada exitosamente', 'success');
    closeModal();
    navigateTo('appointments');
    loadAppointments();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function fetchAvailableSlots() {
  const doctorId = document.getElementById('doctor-select').value;
  const date = document.getElementById('appointment-date').value;
  const timeSelect = document.getElementById('appointment-time');
  timeSelect.innerHTML = '<option value="">Seleccione fecha y doctor primero</option>';
  timeSelect.disabled = true;
  if (!doctorId || !date) return;
  try {
    const slots = await apiCall('GET', `/available-schedules?doctor_id=${doctorId}&date=${date}`);
    const available = slots.filter(s => s.available);
    if (available.length === 0) {
      timeSelect.innerHTML = '<option value="">No hay horarios disponibles</option>';
      return;
    }
    timeSelect.innerHTML = '<option value="">Seleccione un horario</option>';
    available.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.time;
      opt.textContent = s.time;
      timeSelect.appendChild(opt);
    });
    timeSelect.disabled = false;
  } catch {
    timeSelect.innerHTML = '<option value="">Error al cargar horarios</option>';
  }
}

async function createAppointment(e) {
  e.preventDefault();
  const body = {
    doctorId: document.getElementById('doctor-select').value,
    therapyId: document.getElementById('therapy-select').value,
    date: document.getElementById('appointment-date').value,
    time: document.getElementById('appointment-time').value,
    symptoms: document.getElementById('symptoms').value.trim(),
    hasExams: document.getElementById('has-exams').checked,
    exams: document.getElementById('has-exams').checked
      ? document.getElementById('exams').value.split(',').map(s => s.trim()).filter(Boolean)
      : [],
  };
  if (!body.doctorId || !body.therapyId || !body.date || !body.time || !body.symptoms) {
    showToast('Complete todos los campos requeridos', 'error');
    return;
  }
  try {
    await apiCall('POST', '/', body);
    showToast('Cita creada exitosamente', 'success');
    e.target.reset();
    document.getElementById('exams-group').style.display = 'none';
    document.getElementById('appointment-time').innerHTML = '<option value="">Seleccione fecha y doctor primero</option>';
    loadDashboard();
    navigateTo('appointments');
    loadAppointments();
  } catch {
    showToast('Error al crear cita', 'error');
  }
}

async function seedDatabase() {
  if (!confirm('¿Está seguro de poblar la base de datos? Se eliminarán todos los datos existentes.')) return;
  try {
    const res = await fetch(API + '/seed', { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Error al poblar');
    showToast(`Base de datos poblada: ${data.stats?.appointments || 0} citas creadas`, 'success');
    loadDashboard();
    loadDoctorTherapyData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function showToast(msg, type) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast ' + type + ' show';
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), 3000);
}

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
