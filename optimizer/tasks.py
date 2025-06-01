from celery import shared_task
from optimizer.core.cable_optimizer import control_panel  # your refactored function
import pandas as pd
from io import StringIO
from django.conf import settings

import logging
logger = logging.getLogger(__name__)

@shared_task(bind=True, time_limit = settings.OPTIMIZER_TIME_LIMIT)  # 5 minutes timeout
def run_optimizer(self, input_payload):
    try:
        ds_settings = input_payload.get('ds_settings', '[]')
        cables = input_payload.get('cables', '[]')
        drums = input_payload.get('drums', '[]')
        if not cables and not drums:
            error_msg = "Missing cables or drums data"
            logger.error(error_msg)
            self.update_state(state="FAILURE", meta={"error": error_msg})
            raise ValueError(error_msg)
        
        cables_data = pd.read_json(StringIO(cables), orient='records')
        drums_data = pd.read_json(StringIO(drums), orient='records')       
         
        # Call optimization engine
        result = control_panel(cables_data, drums_data, ds_settings)
        logger.info("Optimization completed successfully")       
        # "return result" is replaced by the below two lines. This is to avoid sending large payloads back to the client.
        self.update_state(state='SUCCESS', meta={"ds_report": result})
        return {"message": "Optimization complete"}  # return small payload only

    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise



from celery import shared_task

@shared_task
def dummy_add(x, y):
    return x + y