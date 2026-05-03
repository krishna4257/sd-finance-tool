function accept(feed_id) {

  csrfFetch(`/feed/customer/accept/${feed_id}`, {
    method: "POST"
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      alert("Customer accepted successfully");
      location.reload();
    } else {
      alert("Failed to accept customer");
    }
  })
  .catch(err => {
    console.error(err);
    alert("Server error");
  });

}

function acceptPayment(feed_payment_id) {

csrfFetch(`/feed/payment/accept/${feed_payment_id}`, {
method: "POST"
})
.then(res => res.json())
.then(data => {

if (data.success) {
alert("Payment accepted");
location.reload();
}
else {
alert(data.error);
}

})
.catch(err => {
console.error(err);
alert("Server error");
});

}