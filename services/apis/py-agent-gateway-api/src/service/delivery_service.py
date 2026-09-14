class DeliveryService:

    def __init__(self, senders):
        self._senders = senders

    def deliver(
        self,
        message: dict,
        response: str,
    ) -> None:
        delivery = message['delivery']

        sender = self._senders[
            delivery['type']
        ]

        sender.send(
            delivery=delivery,
            response=response,
        )
