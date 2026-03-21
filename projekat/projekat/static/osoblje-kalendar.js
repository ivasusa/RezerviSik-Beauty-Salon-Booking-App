/* Masa Avramovic */

document.addEventListener("DOMContentLoaded", () => {
  function getCSRFToken() {
    const cookie = document.cookie
      .split("; ")
      .find((row) => row.startsWith("csrftoken="));

    return cookie ? cookie.split("=")[1] : "";
  }

  async function cancelAppointment(id, reloadDate) {
    if (!confirm("Da li ste sigurni da želite da otkažete termin?")) return;

    const res = await fetch(`/osoblje/api/appointments/${id}/cancel/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCSRFToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
    });

    const data = await res.json();

    if (!res.ok) {
      alert(data.error || "Greška pri otkazivanju");
      return;
    }

    loadDay(reloadDate);
  }

  const calRoot = document.getElementById("calendar");
  if (!calRoot) return;

  const apiMonth = calRoot.dataset.apiMonth;
  const apiDay = calRoot.dataset.apiDay;

  let year = parseInt(calRoot.dataset.initialYear, 10);
  let month = parseInt(calRoot.dataset.initialMonth, 10);

  const titleEl = document.getElementById("calendar-title");
  const gridEl = document.getElementById("calendar-grid");
  const dayDetailsEl = document.getElementById("day-details");
  const selectedDateEl = document.getElementById("selected-date");

  const prevBtn = document.getElementById("prev-month");
  const nextBtn = document.getElementById("next-month");

  function ymdToPretty(ymd) {
    const [y, m, d] = ymd.split("-");
    return `${d}.${m}.${y}.`;
  }

  function statusLabel(statusInt) {
    switch (parseInt(statusInt, 10)) {
      case 1:
        return "Rezervisano";
      case 2:
        return "Otkazano";
      case 3:
        return "Završeno";
      default:
        return "Status: " + statusInt;
    }
  }

  async function loadMonth() {
    dayDetailsEl.innerHTML = "";
    selectedDateEl.textContent = "";

    const url = `${apiMonth}?year=${year}&month=${month}`;
    const res = await fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    const data = await res.json();

    if (data.error) {
      titleEl.textContent = "Greška";
      gridEl.innerHTML = `<div class="calendar-error">Greška: ${data.error}</div>`;
      return;
    }

    titleEl.textContent = data.title;

    const header = `
      <div class="calendar-cell header">Pon</div>
      <div class="calendar-cell header">Uto</div>
      <div class="calendar-cell header">Sre</div>
      <div class="calendar-cell header">Čet</div>
      <div class="calendar-cell header">Pet</div>
      <div class="calendar-cell header">Sub</div>
      <div class="calendar-cell header">Ned</div>
    `;

    let body = "";
    for (const week of data.weeks) {
      for (const d of week) {
        const classes = ["calendar-cell", "day"];
        if (!d.in_month) classes.push("muted");
        if (d.has_appointments) classes.push("has-appts");

        body += `
          <button class="${classes.join(" ")}" type="button" data-date="${d.date}">
            <span class="day-number">${d.day}</span>
          </button>
        `;
      }
    }

    gridEl.innerHTML = header + body;

    gridEl.querySelectorAll("button.day[data-date]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const date = btn.dataset.date;

        gridEl
          .querySelectorAll("button.day.selected")
          .forEach((x) => x.classList.remove("selected"));
        btn.classList.add("selected");

        await loadDay(date);
      });
    });
  }

  async function loadDay(date) {
    selectedDateEl.textContent = ymdToPretty(date);
    dayDetailsEl.innerHTML = `<div class="loading">Učitavam termine...</div>`;

    const url = `${apiDay}?date=${date}`;
    const res = await fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    const data = await res.json();

    if (data.error) {
      dayDetailsEl.innerHTML = `<div class="calendar-error">Greška: ${data.error}</div>`;
      return;
    }

    const appts = data.appointments || [];
    if (appts.length === 0) {
      dayDetailsEl.innerHTML = `<div class="empty">Nema termina za ovaj dan.</div>`;
      return;
    }

    const cards = appts
      .map((a) => {
        const time = a.end ? `${a.start} - ${a.end}` : `${a.start}`;
        const st =
          a.status !== undefined && a.status !== null
            ? statusLabel(a.status)
            : "";

        const cancelBtn = a.can_cancel
          ? `<button class="cancel-btn" data-id="${a.id}">Otkaži</button>`
          : "";

        return `
          <div class="schedule-card">
            <div class="schedule-top">
              <div class="schedule-time">${time}</div>
              ${st ? `<div class="schedule-status">${st}</div>` : ``}
            </div>
            <div class="schedule-service">${a.service || ""}</div>
            <div class="schedule-client">Klijent: ${a.client || ""}</div>
            ${cancelBtn}
          </div>
        `;
      })
      .join("");

    dayDetailsEl.innerHTML = cards;

    dayDetailsEl.querySelectorAll(".cancel-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        cancelAppointment(btn.dataset.id, date);
      });
    });
  }

  prevBtn.addEventListener("click", async () => {
    month -= 1;
    if (month === 0) {
      month = 12;
      year -= 1;
    }
    await loadMonth();
  });

  nextBtn.addEventListener("click", async () => {
    month += 1;
    if (month === 13) {
      month = 1;
      year += 1;
    }
    await loadMonth();
  });

  loadMonth();
});