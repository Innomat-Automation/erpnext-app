// Innomat script global script inserts

// mark navbar in specific colour
window.onload = function () {
        setTimeout(function() {
                var navbars = document.getElementsByClassName("navbar");
                if (navbars.length > 0) {
                        if (window.location.hostname.includes("srv-erp-test")) {
                                navbars[0].style.backgroundColor = "#d68080";
                        }
                }
        }, 500);
}
