from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from celery.result import AsyncResult
from django.conf import settings
from .tasks import run_optimizer
from optimizer.core.ds_settings_parser import unpack_ds_settings

import logging
logger = logging.getLogger(__name__)

class OptimizerSubmitView(APIView):
    def post(self, request):
        
        key = request.headers.get("X-Optimizer-Key")
        if key != settings.OPTIMIZER_API_KEY:
            return Response({"error": "Unauthorized"}, status=401)
        
        try:
            cables = request.data.get('cables', '[]')
            drums = request.data.get('drums', '[]')
            ds_settings = request.data.get("ds_settings", {})
            parsed_settings = unpack_ds_settings(ds_settings)
            if not cables or (not parsed_settings.is_pre_order and not drums):
                logger.error("Missing required optimizer payload data in request")
                return Response(
                    {"error": "Cables data and the required drum data are missing"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Queue task using Celery            
              
            task = run_optimizer.delay(request.data)                
            logger.info(f"Task queued with ID: {task.id}")
            # Return the task ID immediately
            return Response(
                {"task_id": task.id, "status": "Task submitted"},
                status=status.HTTP_202_ACCEPTED
                )
        except Exception as e:
            logger.error(f"Failed to submit task: {str(e)}")
            return Response(
                {"error": f"Failed to submit task: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Track Task Status
class OptimizerStatusView(APIView):
    def get(self, request, task_id):
        try:
            task = AsyncResult(task_id)            
            response_data = {"task_id": task_id, "status": task.status,}
                        
            if task.successful():                
                result_data = task.result or task.info or {}
                response_data["result"] = result_data.get("ds_report")
                
            elif task.failed():           
                result_data = str(task.result)
                if "TimeLimitExceeded" in result_data:
                    response_data["result"] = "Optimizer exceeded allowed time limit."
                else:
                    response_data["result"] = result_data
                
            else:
                response_data["result"] = None

            return Response(response_data)
        
        except Exception as e:
            logger.error(f"Failed to retrieve task status {task_id}: {str(e)}")
            return Response(
                {"error": f"Failed to retrieve task status: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
