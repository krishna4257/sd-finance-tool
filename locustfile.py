from locust import HttpUser, task, between, SequentialTaskSet
import random

class UserJourney(SequentialTaskSet):
    valid_anos = [16, 29, 38, 58, 61, 69, 72, 76, 79, 85, 106, 140,
                  288, 289, 297, 318, 322, 346, 347, 358, 361, 362,
                  371, 381, 437, 438, 441, 442, 447, 454, 456, 461,
                  471, 475, 479, 482, 588, 593, 614, 630, 636, 650,
                  668, 674, 677, 679, 696, 698]

    def on_start(self):
        login_response = self.client.post(
            "/login",
            data={
                "username": "test",
                "password": "test@1234",
                "device_id": f"locust-{random.randint(1000,9999)}"
            },
            name="/login"
        )

        if login_response.status_code != 200:
            login_response.failure("Login failed")
            self.interrupt()

        context_response = self.client.post(
            "/set_context",
            json={"vid": 110001},
            name="/set_context"
        )

        if context_response.status_code != 200:
            context_response.failure("Context setup failed")
            self.interrupt()

    @task
    def realistic_user_flow(self):
        self.client.get("/dashboard", name="/dashboard")

        self.client.get("/view_customers", name="/view_customers")

        ano = random.choice(self.valid_anos)

        self.client.post(
            "/search",
            data={"query": str(ano)},
            name="/search"
        )

        self.client.get("/post_payment", name="/post_payment")

        payment_payload = [{
            "ano": int(ano),
            "amt": random.choice([200, 300, 400, 500]),
            "pdt": "01/04/2026"
        }]

        self.client.post(
            "/submit_post_payment",
            json=payment_payload,
            name="/submit_post_payment"
        )

        self.client.get(
            "/post_payment_report",
            name="/post_payment_report"
        )


class SDUser(HttpUser):
    wait_time = between(2, 5)
    tasks = [UserJourney]