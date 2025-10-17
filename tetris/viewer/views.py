from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from db.models import HandlingUnit, Shipment, Simulation

def index(request):
    return render(request, 'viewer/index.html')

@csrf_exempt
@require_http_methods(["POST"])
def add_item(request):
    try:
        data = json.loads(request.body)

        # Get or create shipment
        shipment, created = Shipment.objects.get_or_create(
            id=data['shipment'],
            defaults={'name': f"Shipment {data['shipment']}"}
        )

        # Create handling unit
        item = HandlingUnit.objects.create(
            id=data['id'],
            weight=float(data['weight']),
            x_size=float(data['x_size']),
            y_size=float(data['y_size']),
            z_size=float(data['z_size']),
            shipment=shipment,
            stop=data['stop'],
            temp_add=None
        )

        return JsonResponse({
            'success': True,
            'message': f'Item {item.id} added successfully!',
            'item': {
                'id': item.id,
                'weight': item.weight,
                'x_size': item.x_size,
                'y_size': item.y_size,
                'z_size': item.z_size,
                'shipment': item.shipment.id,
                'stop': item.stop
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error adding item: {str(e)}'
        }, status=400)

@require_http_methods(["GET"])
def get_items(request):
    try:
        items = HandlingUnit.objects.all().values(
            'id', 'weight', 'x_size', 'y_size', 'z_size', 'shipment', 'stop'
        )
        return JsonResponse({
            'success': True,
            'items': list(items)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error fetching items: {str(e)}'
        }, status=400)