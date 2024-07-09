const spinnerWrapperE1 = document.querySelector('.spinner-wrapper');

window.addEventListener("load", () => {
    spinnerWrapperE1.style.opacity = "0";

    setTimeout(() => {
        spinnerWrapperE1.style.display = "none";
    }, 200);
});


// Add event listener to trigger toast on button click
document.getElementById('liveToastBtn').addEventListener('click', function() {
    var toast = new bootstrap.Toast(document.getElementById('liveToast'));
    toast.show();
});