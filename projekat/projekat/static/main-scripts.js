// Autori: Iva Šuša, Sandra Bubanja, Jovana Simić



function selectUserType(type) {
    document.getElementById('user-type-selection').classList.add('hidden');
    if (type === 'client') {
        document.getElementById('client-registration').classList.remove('hidden');
    } else if (type === 'owner') {
        document.getElementById('owner-registration').classList.remove('hidden');
    }
}

function resetRegistration() {
    document.getElementById('client-registration').classList.add('hidden');
    document.getElementById('owner-registration').classList.add('hidden');
    document.getElementById('user-type-selection').classList.remove('hidden');
    document.getElementById('client-registration').reset();
    document.getElementById('owner-registration').reset();
    document.getElementById('client-message').classList.add('hidden');
    document.getElementById('owner-message').classList.add('hidden');
}

function filterSalons() {
    const searchName = document.getElementById('search-name').value.toLowerCase();
    const filterCategory = document.getElementById('filter-category').value;
    const filterRating = parseFloat(document.getElementById('filter-rating').value) || 0;
    const salonCards = document.querySelectorAll('.salon-card');
    const noResults = document.getElementById('no-results');
    let visibleCount = 0;
    
    salonCards.forEach(card => {
        const name = card.querySelector('h3').textContent.toLowerCase();
        const category = card.getAttribute('data-category');
        const rating = parseFloat(card.getAttribute('data-rating'));
        
        const matchesName = !searchName || name.includes(searchName);
        const matchesCategory = !filterCategory || category === filterCategory;
        const matchesRating = rating >= filterRating;
        
        if (matchesName && matchesCategory && matchesRating) {
            card.style.display = 'block';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });
    
    if (visibleCount === 0) {
        noResults.classList.remove('hidden');
    } else {
        noResults.classList.add('hidden');
    }
}

function resetFilters() {
    document.getElementById('search-name').value = '';
    document.getElementById('filter-category').value = '';
    document.getElementById('filter-rating').value = '';
    filterSalons();
}


function confirmLogout() {
    if (confirm('Da li ste sigurni da se želite odjaviti?')) {
        window.location.href = 'home.html';
    }
}

function approveOwner(ownerName, salonName) {
    if (confirm(`Da li ste sigurni da želite da odobrite registraciju za ${ownerName} (${salonName})?`)) {
        alert(`Registracija za ${ownerName} je uspešno odobrena. Vlasnik salona je obavešten putem email-a.`);
    }
}

function rejectOwner(ownerName, salonName) {
    const reason = prompt(`Unesite razlog odbijanja registracije za ${ownerName} (${salonName}):`);
    if (reason) {
        alert(`Registracija za ${ownerName} je odbijena. Razlog: ${reason}`);
    }
}

function setRating(rating) {
    document.getElementById('review-rating').value = rating;
    
    const starBtns = document.querySelectorAll('.star-btn');
    starBtns.forEach((btn, index) => {
        if (index < rating) {
            btn.style.color = '#ffd700';
        } else {
            btn.style.color = '#ccc';
        }
    });
}
function showAddServiceForm() {
            document.getElementById('add-service-form').classList.remove('hidden');
        }

        function hideAddServiceForm() {
            document.getElementById('add-service-form').classList.add('hidden');
        }

        function showAddStaffForm() {
            document.getElementById('add-staff-form').classList.remove('hidden');
        }

        function hideAddStaffForm() {
            document.getElementById('add-staff-form').classList.add('hidden');
            document.getElementById('staff-form').reset();
            document.getElementById('staff-message').classList.add('hidden');
        }

        function confirmDeleteStaff(staffName) {
            if (confirm(`Da li ste sigurni da želite da obrišete nalog za ${staffName}?`)) {
                alert(`Nalog za ${staffName} je uspešno obrisan.`);
            }
        }


        function filterReviews() {
            const filterValue = document.getElementById('review-filter-marks').value;
            const reviewCards = document.querySelectorAll('.review-card');
            
            reviewCards.forEach(card => {
                const rating = card.getAttribute('data-rating');
                if (!filterValue || rating === filterValue) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        }


async function loadSalonStats(salonId) {
  try {
    const response = await fetch(`/api/salon-stats/${salonId}/`);

    if (!response.ok) {
      console.error("Stats API error:", response.status);
      return;
    }

    const data = await response.json();

    document.querySelector('.stat-card:nth-child(1) .stat-number').textContent = data.total_appointments ?? 0;
    document.querySelector('.stat-card:nth-child(2) .stat-number').textContent = data.canceled_appointments ?? 0;
    document.querySelector('.stat-card:nth-child(3) .stat-number').textContent = (data.total_earnings ?? 0).toLocaleString();
    document.querySelector('.stat-card:nth-child(4) .stat-number').textContent = (data.avg_rating ?? 0).toFixed(1);
  } catch (err) {
    console.error('Greška pri učitavanju statistike:', err);
  }
}


document.addEventListener('DOMContentLoaded', () => {
  const statsContainer = document.getElementById("owner-stats");

  if (!statsContainer) return;

  const salonId = statsContainer.dataset.salonId;
  loadSalonStats(salonId);

  setInterval(() => loadSalonStats(salonId), 10000);
});


const dateInput = document.getElementById("appointment-date");
const timeSelect = document.getElementById("appointment-time");
console.log("ljj")
if (dateInput && timeSelect) {
  dateInput.addEventListener("change", async (e) => {
    const date = e.target.value;
    console.log("Picked date:", date);

    const url = `/staff/free-slots-test/${date}/`;
    console.log("Fetching:", url);

    const res = await fetch(url);
    console.log("Status:", res.status);

    const data = await res.json();
    console.log("Data:", data);

    timeSelect.innerHTML = `<option value="">Izaberite vreme</option>`;

    if (!Array.isArray(data)) {
      alert(data.error || "Greška pri učitavanju termina");
      return;
    }

    data.forEach((t) => {
      timeSelect.innerHTML += `<option value="${t}">${t}</option>`;
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const details = document.getElementById("day-details");
  const dayCells = document.querySelectorAll(".calendar-day[data-date]");

  if (!details || dayCells.length === 0) return;

  async function loadDay(dateStr) {
    try {
      const res = await fetch(`/staff/day-test/${dateStr}/`);
      const data = await res.json();

      details.innerHTML = "";

      if (data.error) {
        details.innerHTML = `<div class="notification">${data.error}</div>`;
        return;
      }

      if (!Array.isArray(data) || data.length === 0) {
        details.innerHTML = `<div class="notification">Nema termina za ovaj dan.</div>`;
        return;
      }

      data.forEach(a => {
        details.innerHTML += `
          <div class="schedule-card">
            <h4>${a.time} - ${a.client}</h4>
            <p>Usluga: ${a.service}</p>
          </div>
        `;
      });

    } catch (e) {
      console.error(e);
      details.innerHTML = `<div class="notification">Greška pri učitavanju termina.</div>`;
    }
  }

  dayCells.forEach(cell => {
    cell.addEventListener("click", () => {
      const dateStr = cell.getAttribute("data-date");
      loadDay(dateStr);
    });
  });
});

document.addEventListener("DOMContentLoaded", () => {

    let currentMonth = 7;
    let currentYear = 2025;

    const monthNames = [
        "Januar", "Februar", "Mart", "April", "Maj", "Jun",
        "Jul", "Avgust", "Septembar", "Oktobar", "Novembar", "Decembar"
    ];

    const grid = document.getElementById("calendar-grid");
    const title = document.getElementById("calendar-title");
    const prevBtn = document.getElementById("prev-month");
    const nextBtn = document.getElementById("next-month");

    const details = document.getElementById("day-details");
    const selectedTitle = document.getElementById("selected-day-title");

    if (!grid || !title || !prevBtn || !nextBtn) return;

    function pad2(n) { return String(n).padStart(2, "0"); }

    function formatDate(year, month0, day) {

        return `${year}-${pad2(month0 + 1)}-${pad2(day)}`;
    }

    function clearSelectedDay() {
        const all = grid.querySelectorAll(".calendar-day[data-date]");
        all.forEach(el => el.classList.remove("selected-day"));
    }

    async function loadDay(date) {
  try {
    const url = `/staff/day-test/${date}/`;
    const res = await fetch(url);

    if (!res.ok) {
      const txt = await res.text();
      console.error("HTTP greška:", res.status, txt);
      throw new Error(`HTTP ${res.status}`);
    }

    const data = await res.json();
    console.log("DAY DATA:", data);

    const title = document.getElementById("selected-day-title");
    const container = document.getElementById("day-details");
    title.innerText = `Termini za ${date}`;
    container.innerHTML = "";

    if (data.length === 0) {
      container.innerHTML = "<p>Nema termina za ovaj dan.</p>";
      return;
    }

    data.forEach(a => {
      container.innerHTML += `
        <div class="schedule-card">
          <h4>${a.time} - ${a.client}</h4>
          <p>${a.service}</p>
        </div>`;
    });

  } catch (err) {
    console.error("Greška pri učitavanju:", err);
    const container = document.getElementById("day-details");
    if (container) container.innerHTML = "<p style='color:red'>Greška pri učitavanju termina.</p>";
  }
}


    function markBookedDays(year, month0) {

        fetch(`/staff/api/booked-days-test/${year}/${month0 + 1}/`)
            .then(res => res.json())
            .then(days => {
                if (!Array.isArray(days)) return;

                days.forEach(d => {
                    const dateStr = formatDate(year, month0, d);
                    const el = grid.querySelector(`.calendar-day[data-date="${dateStr}"]`);
                    if (el) el.classList.add("booked");
                });
            })
            .catch(() => {});
    }

    function renderCalendar(month0, year) {
        grid.innerHTML = "";

        ["Pon","Uto","Sre","Čet","Pet","Sub","Ned"].forEach(d => {
            grid.innerHTML += `<div class="calendar-day">${d}</div>`;
        });

        title.textContent = `${monthNames[month0]} ${year}`;

        const firstDay = new Date(year, month0, 1).getDay();
        const start = (firstDay === 0) ? 6 : firstDay - 1;
        const daysInMonth = new Date(year, month0 + 1, 0).getDate();

        for (let i = 0; i < start; i++) {
            grid.innerHTML += `<div class="calendar-day empty"></div>`;
        }

        for (let d = 1; d <= daysInMonth; d++) {
            const dateStr = formatDate(year, month0, d);
            grid.innerHTML += `<div class="calendar-day" data-date="${dateStr}">${d}</div>`;
        }


        const clickable = grid.querySelectorAll(".calendar-day[data-date]");
        clickable.forEach(cell => {
            cell.addEventListener("click", () => {
                clearSelectedDay();
                cell.classList.add("selected-day");
                loadDay(cell.dataset.date);
            });
        });

        markBookedDays(year, month0);
    }

    prevBtn.addEventListener("click", () => {
        currentMonth--;
        if (currentMonth < 0) {
            currentMonth = 11;
            currentYear--;
        }
        renderCalendar(currentMonth, currentYear);
    });

    nextBtn.addEventListener("click", () => {
        currentMonth++;
        if (currentMonth > 11) {
            currentMonth = 0;
            currentYear++;
        }
        renderCalendar(currentMonth, currentYear);
    });

    renderCalendar(currentMonth, currentYear);
});

document.addEventListener("DOMContentLoaded", () => {
  const grid = document.getElementById("owner-calendar-grid");
  const titleEl = document.getElementById("owner-calendar-title");
  const prevBtn = document.getElementById("owner-prev-month");
  const nextBtn = document.getElementById("owner-next-month");

  const selectedTitle = document.getElementById("owner-selected-day-title");
  const details = document.getElementById("owner-day-details");

  if (!grid || !titleEl || !prevBtn || !nextBtn) return;

  let currentMonth = 7;
  let currentYear = 2025;

  const monthNames = [
    "Januar", "Februar", "Mart", "April", "Maj", "Jun",
    "Jul", "Avgust", "Septembar", "Oktobar", "Novembar", "Decembar"
  ];

  const pad2 = (n) => String(n).padStart(2, "0");
  const formatDate = (y, m0, d) => `${y}-${pad2(m0 + 1)}-${pad2(d)}`;

  function clearSelectedDay() {
    grid.querySelectorAll(".calendar-day.selected-day").forEach(x => x.classList.remove("selected-day"));
  }

  function renderCalendar(month0, year) {
    grid.innerHTML = "";

    ["Pon","Uto","Sre","Čet","Pet","Sub","Ned"].forEach(d => {
      grid.innerHTML += `<div class="calendar-day">${d}</div>`;
    });

    titleEl.textContent = `${monthNames[month0]} ${year}`;

    const firstDay = new Date(year, month0, 1).getDay();
    const start = (firstDay === 0) ? 6 : firstDay - 1;
    const daysInMonth = new Date(year, month0 + 1, 0).getDate();

    for (let i = 0; i < start; i++) {
      grid.innerHTML += `<div class="calendar-day empty"></div>`;
    }


    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = formatDate(year, month0, d);
      grid.innerHTML += `<div class="calendar-day" data-date="${dateStr}">${d}</div>`;
    }

    grid.querySelectorAll(".calendar-day[data-date]").forEach(cell => {
      cell.addEventListener("click", () => {
        clearSelectedDay();
        cell.classList.add("selected-day");
        loadOwnerDay(cell.dataset.date);
      });
    });

    console.log("Rendering owner calendar for:", year, month0 + 1);
   markOwnerBookedDays(grid,year, month0);

  }

  async function loadOwnerDay(dateStr) {
    try {
      const res = await fetch(`/owner/day-test/${dateStr}/`);
      const data = await res.json();

      if (selectedTitle) selectedTitle.textContent = `Rezervacije za ${dateStr}`;
      if (!details) return;

      details.innerHTML = "";

      if (data && data.error) {
        details.innerHTML = `<div class="notification">${data.error}</div>`;
        return;
      }

      if (!Array.isArray(data) || data.length === 0) {
        details.innerHTML = `<div class="notification">Nema rezervacija za ovaj dan.</div>`;
        return;
      }

      data.forEach(a => {
        details.innerHTML += `
          <div class="schedule-card">
            <h4>${a.time} - ${a.client}</h4>
            <p>Usluga: ${a.service}</p>
          </div>
        `;
      });

    } catch (e) {
      console.error("OWNER load day error:", e);
      if (details) details.innerHTML = `<div class="notification">Greška pri učitavanju.</div>`;
    }
  }

  prevBtn.addEventListener("click", () => {
    currentMonth--;
    if (currentMonth < 0) { currentMonth = 11; currentYear--; }
    renderCalendar(currentMonth, currentYear);
  });

  nextBtn.addEventListener("click", () => {
    currentMonth++;
    if (currentMonth > 11) { currentMonth = 0; currentYear++; }
    renderCalendar(currentMonth, currentYear);
  });

  renderCalendar(currentMonth, currentYear);
});

function markOwnerBookedDays(gridEl, year, month0) {
  const url = `/owner/api/booked-days-test/${year}/${month0 + 1}/`;
  console.log("fetching booked days:", url);

  fetch(url)
    .then(res => {
      console.log("status booked-days:", res.status);
      return res.json();
    })
    .then(days => {
      console.log(" booked days data:", days);
      if (!Array.isArray(days)) return;

      days.forEach(d => {
        const dateStr = `${year}-${String(month0 + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
        const el = gridEl.querySelector(`.calendar-day[data-date="${dateStr}"]`);
        if (el) el.classList.add("booked");
      });
    })
    .catch(err => console.error("booked-days error:", err));
}

function showActionPopup(message, type="success", seconds=4, title="") {

    const container = document.getElementById("toast-container");
    if(!container){
        console.warn("toast-container ne postoji u HTML-u");
        return;
    }

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;

    toast.innerHTML = `
        ${title ? `<div class="toast-title">${title}</div>` : ""}
        <div>${message}</div>
    `;

    container.appendChild(toast);

    requestAnimationFrame(()=> toast.classList.add("show"));

    setTimeout(()=>{
        toast.classList.remove("show");
        setTimeout(()=> toast.remove(), 300);
    }, seconds * 1000);
}


document.addEventListener("DOMContentLoaded", () => {
  const holder = document.getElementById("django-messages");
  if (!holder) return;

  holder.querySelectorAll("div[data-level][data-text]").forEach(el => {
    const level = el.dataset.level;
    const text = el.dataset.text;

    let type = "info";
    if (level.includes("success")) type = "success";
    else if (level.includes("error")) type = "error";
    else if (level.includes("warning")) type = "error";

    showActionPopup(text, type, 4, "Obaveštenje");
  });
});




