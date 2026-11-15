from queue_store import Queue
from warehouse import Warehouse, encoded


class ResponseLost(RuntimeError):
    pass


def apply(warehouse_path, queue_path, record, attempt, payload,
          hook=lambda name: None, lose_response=False):
    if not isinstance(record, str) or not record or not isinstance(attempt, str) or not attempt:
        raise ValueError("invalid correction identity")
    encoded(payload)
    queue = Queue(queue_path)
    warehouse = Warehouse(warehouse_path)
    try:
        queue.stage(record, attempt, payload)
        hook("staged")
        receipt = warehouse.accept(record, payload, attempt=attempt)
        hook("warehouse_committed")
        if lose_response:
            raise ResponseLost("receipt response lost after commit")
        hook("before_close")
        queue.finish(record, receipt)
        hook("after_close")
        return receipt
    finally:
        warehouse.close()
        queue.close()
