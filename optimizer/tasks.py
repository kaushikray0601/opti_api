from celery import shared_task
from io import StringIO
import logging

import pandas as pd
from django.conf import settings

from optimizer.core.cable_optimizer import control_panel

logger = logging.getLogger(__name__)

@shared_task(bind=True, time_limit=settings.OPTIMIZER_TIME_LIMIT)
def run_optimizer(self, input_payload):
    ds_settings = input_payload.get('ds_settings', '[]')
    cables = input_payload.get('cables', '[]')
    drums = input_payload.get('drums', '[]')

    if not cables or not drums:
        error_msg = "Cables and drums data are required"
        logger.error(error_msg)
        raise ValueError(error_msg)

    cables_data = pd.read_json(StringIO(cables), orient='records')
    drums_data = pd.read_json(StringIO(drums), orient='records')

    result = control_panel(cables_data, drums_data, ds_settings)
    if "error" in result:
        logger.error(result["error"])
        raise ValueError(result["error"])
    logger.info("Optimization completed successfully")
    return {"ds_report": result}


@shared_task
def dummy_add(x, y):
    return x + y
