from celery import shared_task
from io import StringIO
import logging

import pandas as pd
from django.conf import settings

from optimizer.core.cable_optimizer import control_panel
from optimizer.core.ds_settings_parser import unpack_ds_settings

logger = logging.getLogger(__name__)

@shared_task(bind=True, time_limit=settings.OPTIMIZER_TIME_LIMIT)
def run_optimizer(self, input_payload):
    ds_settings = input_payload.get('ds_settings', '[]')
    cables = input_payload.get('cables', '[]')
    drums = input_payload.get('drums', '[]')
    parsed_settings = unpack_ds_settings(ds_settings)

    if not cables:
        error_msg = "Cables data is required"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not parsed_settings.is_pre_order and not drums:
        error_msg = "Drums data are required"
        logger.error(error_msg)
        raise ValueError(error_msg)

    cables_data = _read_records_payload(cables)
    drums_data = _read_records_payload(drums)

    result = control_panel(cables_data, drums_data, ds_settings)
    if "error" in result:
        logger.error(result["error"])
        raise ValueError(result["error"])
    logger.info("Optimization completed successfully")
    return {"ds_report": result}


@shared_task
def dummy_add(x, y):
    return x + y


def _read_records_payload(payload):
    if isinstance(payload, pd.DataFrame):
        return payload.copy()

    if isinstance(payload, list):
        return pd.DataFrame(payload)

    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return pd.DataFrame()
        return pd.read_json(StringIO(text), orient='records')

    return pd.DataFrame()
