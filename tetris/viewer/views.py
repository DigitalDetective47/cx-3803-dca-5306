from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import csv
import io
from db.models import HandlingUnit, Shipment, Simulation

def load_selection(request):
    # Landing page showing all loads
    return render(request, 'viewer/load_selection.html')

def load_view(request, simulation_id):
    # 3D viewer for a specific load
    simulation = get_object_or_404(Simulation, id=simulation_id)
    return render(request, 'viewer/index.html', {'simulation': simulation})

@csrf_exempt
@require_http_methods(["POST"])
def add_item(request):
    try:
        data = json.loads(request.body)

        # Get simulation if provided
        simulation = None
        if 'simulation_id' in data and data['simulation_id']:
            simulation = get_object_or_404(Simulation, id=data['simulation_id'])

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
            temp_add=simulation
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
        simulation_id = request.GET.get('simulation_id')

        # Filter by simulation if provided
        if simulation_id:
            items = HandlingUnit.objects.filter(temp_add_id=simulation_id).values(
                'id', 'weight', 'x_size', 'y_size', 'z_size', 'shipment', 'stop'
            )
        else:
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

@require_http_methods(["GET"])
def get_simulations(request):
    # Get all simulations/loads
    try:
        simulations = Simulation.objects.all().values('id', 'name', 'time').order_by('-time')
        return JsonResponse({
            'success': True,
            'simulations': list(simulations)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error fetching simulations: {str(e)}'
        }, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def create_load(request):
    # Create a new load/simulation
    try:
        data = json.loads(request.body)
        simulation = Simulation.objects.create(name=data['name'])
        return JsonResponse({
            'success': True,
            'message': f'Load "{simulation.name}" created successfully!',
            'simulation': {
                'id': simulation.id,
                'name': simulation.name,
                'time': simulation.time.isoformat()
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating load: {str(e)}'
        }, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def import_csv(request):
    # Import items from CSV file
    try:
        simulation_id = request.POST.get('simulation_id')
        csv_file = request.FILES.get('csv_file')

        if not csv_file:
            return JsonResponse({
                'success': False,
                'message': 'No CSV file provided'
            }, status=400)

        if not simulation_id:
            return JsonResponse({
                'success': False,
                'message': 'No simulation ID provided'
            }, status=400)

        simulation = get_object_or_404(Simulation, id=simulation_id)

        # Read and parse CSV (handle BOM)
        csv_data = csv_file.read().decode('utf-8-sig')  # utf-8-sig removes BOM
        csv_reader = csv.DictReader(io.StringIO(csv_data))

        items_created = 0
        errors = []

        for row in csv_reader:
            try:
                # Get or create shipment
                shipment, _ = Shipment.objects.get_or_create(
                    id=int(row['Shipment']),
                    defaults={'name': f"Shipment {row['Shipment']}"}
                )

                # Create handling unit
                HandlingUnit.objects.create(
                    id=row['HU Number'],
                    weight=float(row['Gross Weight']),
                    x_size=float(row['Length']),
                    y_size=float(row['Width']),
                    z_size=float(row['Height']),
                    shipment=shipment,
                    stop=row['Stop'],
                    temp_add=simulation
                )
                items_created += 1
            except Exception as e:
                errors.append(f"Row {row.get('HU Number', 'unknown')}: {str(e)}")

        return JsonResponse({
            'success': True,
            'message': f'Successfully imported {items_created} items',
            'items_created': items_created,
            'errors': errors
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error importing CSV: {str(e)}'
        }, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def create_load_with_csv(request):
    # Create a new load and import CSV items in one operation
    try:
        load_name = request.POST.get('name')
        csv_file = request.FILES.get('csv_file')

        if not load_name:
            return JsonResponse({
                'success': False,
                'message': 'No load name provided'
            }, status=400)

        if not csv_file:
            return JsonResponse({
                'success': False,
                'message': 'No CSV file provided'
            }, status=400)

        # Create simulation
        simulation = Simulation.objects.create(name=load_name)

        # Read and parse CSV (handle BOM)
        csv_data = csv_file.read().decode('utf-8-sig')  # utf-8-sig removes BOM
        csv_reader = csv.DictReader(io.StringIO(csv_data))

        items_created = 0
        errors = []

        for row in csv_reader:
            try:
                # Get or create shipment
                shipment, _ = Shipment.objects.get_or_create(
                    id=int(row['Shipment']),
                    defaults={'name': f"Shipment {row['Shipment']}"}
                )

                # Create handling unit
                HandlingUnit.objects.create(
                    id=row['HU Number'],
                    weight=float(row['Gross Weight']),
                    x_size=float(row['Length']),
                    y_size=float(row['Width']),
                    z_size=float(row['Height']),
                    shipment=shipment,
                    stop=row['Stop'],
                    temp_add=simulation
                )
                items_created += 1
            except Exception as e:
                errors.append(f"Row {row.get('HU Number', 'unknown')}: {str(e)}")

        return JsonResponse({
            'success': True,
            'message': f'Load "{simulation.name}" created with {items_created} items',
            'simulation': {
                'id': simulation.id,
                'name': simulation.name,
                'time': simulation.time.isoformat()
            },
            'items_created': items_created,
            'errors': errors
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating load: {str(e)}'
        }, status=400)