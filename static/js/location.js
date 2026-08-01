async function fetchLocationByPin() {

    const pin = document.getElementById("pincode").value.trim();

    if (pin.length !== 6) {
        return;
    }

    try {

        const response = await fetch(
            `https://api.postalpincode.in/pincode/${pin}`
        );

        const data = await response.json();

        console.log(data);

        if (
            data[0].Status === "Success" &&
            data[0].PostOffice &&
            data[0].PostOffice.length > 0
        ) {

            const office = data[0].PostOffice[0];

            document.getElementById("state").value = office.State;
            document.getElementById("city").value = office.Block ;

        } else {

            document.getElementById("state").value = "";
            document.getElementById("city").value = "";

            Swal.fire({
                icon: "warning",
                title: "Invalid PIN",
                text: "PIN Code not found."
            });

        }

    } catch (err) {

    console.error("PIN API Error:", err);

    Swal.fire({
        icon: "error",
        title: "Network Error",
        text: err.message
    });

}

}