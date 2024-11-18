// static/js/cart.js
document.addEventListener('DOMContentLoaded', function() {
    // Обновление итоговой суммы при изменении количества
    const quantityInputs = document.querySelectorAll('.quantity-input');
    quantityInputs.forEach(input => {
        input.addEventListener('change', function() {
            const row = this.closest('.cart-item');
            const price = parseFloat(row.dataset.price);
            const quantity = parseInt(this.value);
            const total = price * quantity;
            
            row.querySelector('.item-total').textContent = `${total.toFixed(2)} ₽`;
            updateCartTotal();
        });
    });

    function updateCartTotal() {
        const totals = Array.from(document.querySelectorAll('.item-total'))
            .map(el => parseFloat(el.textContent));
        const cartTotal = totals.reduce((a, b) => a + b, 0);
        document.getElementById('cart-total').textContent = `${cartTotal.toFixed(2)} ₽`;
    }

    // Проверка формы оформления заказа
    const checkoutForm = document.getElementById('checkout-form');
    if (checkoutForm) {
        checkoutForm.addEventListener('submit', function(e) {
            const requiredFields = this.querySelectorAll('[required]');
            let isValid = true;

            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('error');
                } else {
                    field.classList.remove('error');
                }
            });

            if (!isValid) {
                e.preventDefault();
                alert('Пожалуйста, заполните все обязательные поля');
            }
        });
    }
});