/* Masa Avramovic */
document.addEventListener("DOMContentLoaded", () => {
  const root = document.getElementById("staff-booking");
  if (!root) return;

  const apiFree = root.dataset.apiFree;
  const apiBook = root.dataset.apiBook;
  const minDate = root.dataset.minDate;
  const csrfToken = root.dataset.csrf;

  const form = document.getElementById("staff-booking-form");
  const msg = document.getElementById("booking-message");

  if (!form) {
    console.error("Nema #staff-booking-form u DOM-u.");
    return;
  }
  if (!msg) {
    console.error("Nema #booking-message u DOM-u.");
    return;
  }

  const elName = document.getElementById("client-name");
  const elPhone = document.getElementById("client-phone");
  const elEmail = document.getElementById("client-email");

  const elService = document.getElementById("service-id");
  const elStaff = document.getElementById("staff-id");
  const elDate = document.getElementById("appointment-date");
  const elTime = document.getElementById("appointment-time");

  if (minDate && elDate) elDate.min = minDate;

  function showMessage(text, ok) {
    msg.textContent = text;
    msg.classList.remove("hidden");
    msg.classList.remove("ok", "err");
    msg.classList.add(ok ? "ok" : "err");
  }

  function hideMessage() {
    msg.classList.add("hidden");
    msg.textContent = "";
    msg.classList.remove("ok", "err");
  }

  function clearTimes() {
    elTime.innerHTML = `<option value="">Izaberite vreme</option>`;
  }

  async function safeJson(res) {
    const text = await res.text();
    try {
      return JSON.parse(text);
    } catch {
      return { error: text || "Neočekivan odgovor sa servera." };
    }
  }

  async function loadFreeSlots() {
    clearTimes();

    const date = elDate.value;
    const serviceId = elService.value;
    const staffId = elStaff.value;

    if (!date || !serviceId || !staffId) return;

    const url =
      `${apiFree}?date=${encodeURIComponent(date)}` +
      `&service_id=${encodeURIComponent(serviceId)}` +
      `&staff_id=${encodeURIComponent(staffId)}`;

    const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    const data = await safeJson(res);

    if (!res.ok || data.error) {
      showMessage(data.error || "Greška pri učitavanju slobodnih termina.", false);
      return;
    }

    const slots = Array.isArray(data) ? data : [];

    if (slots.length === 0) {
      showMessage("Nema slobodnih termina za izabrani datum/uslugu/osoblje.", false);
      return;
    }

    const uniqueTimes = [...new Set(slots.map(item => item.time))];

    for (const t of uniqueTimes) {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t;
      elTime.appendChild(opt);
    }
  }

  elService.addEventListener("change", () => {
    hideMessage();
    loadFreeSlots();
  });

  elStaff.addEventListener("change", () => {
    hideMessage();
    loadFreeSlots();
  });

  elDate.addEventListener("change", () => {
    hideMessage();
    loadFreeSlots();
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (!form.checkValidity()) {
      form.reportValidity();
      showMessage("Popuni sva obavezna polja.", false);
      return;
    }

    if (!elTime.value) {
      showMessage("Izaberi vreme.", false);
      return;
    }

    hideMessage();

    const payload = {
      client_name: elName.value.trim(),
      client_phone: elPhone.value.trim(),
      client_email: elEmail.value.trim(),
      date: elDate.value,
      time: elTime.value,
      service_id: parseInt(elService.value, 10),
      staff_id: parseInt(elStaff.value, 10),
    };

    const res = await fetch(apiBook, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify(payload),
    });

    const data = await safeJson(res);

    if (!res.ok || data.error) {
      showMessage(data.error || "Greška pri zakazivanju.", false);
      return;
    }

    await loadFreeSlots();
    showMessage("Uspešno zakazan termin.", true);
    elTime.value = "";
  });
});
