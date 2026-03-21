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