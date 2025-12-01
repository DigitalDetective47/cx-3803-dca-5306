from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from django.db import transaction
import csv
import io
from .models import HandlingUnit, Shipment, Simulation, SimPlacement, SavedConfiguration, SavedPlacement
from .algo import compute_layout
from .restrictions import Restriction

STOP_COLOR_MAP = {
    "1A": "#3b82f6",  # blue
    "2A": "#22c55e",  # green
    "3A": "#f97316",  # orange
    "4A": "#a855f7",  # purple
}

DEFAULT_STOP_COLOR = "#9ca3af"  # grey for anything else

def color_for_stop(stop_raw):
    s = (stop_raw or "").strip()
    return STOP_COLOR_MAP.get(s, DEFAULT_STOP_COLOR)

def load_selection(request):
    # Landing page showing all loads
    return render(request, 'viewer/load_selection.html')

@csrf_exempt
def run_algo(request, simulation_id):
    simulation = get_object_or_404(Simulation, id=simulation_id)
    print("here")
    compute_layout(simulation)

    return JsonResponse({"status": "ok"})

def load_view(request, simulation_id):
    # 3D viewer for a specific load
    simulation = get_object_or_404(Simulation, id=simulation_id)
    # compute_layout(simulation)
    return render(request, 'viewer/index.html', {'simulation': simulation})

@csrf_exempt
def delete_load(request, load_id):
    if request.method != "DELETE":
        return JsonResponse({"success": False, "message": "Invalid request method"}, status=405)

    try:
        load = Simulation.objects.get(id=load_id)
        load.delete()
        return JsonResponse({"success": True, "message": "Load deleted successfully."})
    except Simulation.DoesNotExist:
        return JsonResponse({"success": False, "message": "Load not found."}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def add_item(request):
    try:
        data = json.loads(request.body)
        stop_value = (data.get("stop") or "").strip()

        simulation = None
        if 'simulation_id' in data and data['simulation_id']:
            simulation = get_object_or_404(Simulation, id=data['simulation_id'])

        shipment, created = Shipment.objects.get_or_create(
            id=data['shipment'],
            defaults={'name': f"Shipment {data['shipment']}"}
        )

        item = HandlingUnit.objects.create(
            id=data['id'],
            weight=float(data['weight']),
            x_size=float(data['x_size']),
            y_size=float(data['y_size']),
            z_size=float(data['z_size']),
            shipment=shipment,
            stop=stop_value,
            color=color_for_stop(stop_value),
            temp_add=simulation
        )
    #     SimPlacement.objects.get_or_create(
    #       sim=simulation,
    #       handling_unit=data['id'],
    #       defaults={
              
    #           "orientation": ,
    #           "temp_remove": False,
    #       }
    #   )
        
        # SimPlacement.objects.update_or_create(
        #     hu=item,
        #     sim=simulation,
        #     defaults={
        #         "x": 0.0,
        #         "y": 0.0,
        #         "z": 0.0,
        #         "orientation": "XYZ",
        #         "temp_remove": False
        #     }
        # )

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
                'stop': item.stop,
                'color': item.color,
            }
        })
    except Exception as e:
        error_message = str(e)
        if 'UNIQUE constraint failed' in error_message or 'already exists' in error_message:
            message = 'Error adding item. HU ID already exists.'
        else:
            message = 'Error adding item. Please check your input and try again.'

        return JsonResponse({
            'success': False,
            'message': message
        }, status=400)
    

@csrf_exempt
@require_http_methods(["POST"])
def save_configuration(request, simulation_id):
    """
    Save current SimPlacement rows for a simulation into a new SavedConfiguration.
    Expects JSON: {"name": "Optional name"}
    """
    try:
        sim = get_object_or_404(Simulation, id=simulation_id)
        data = json.loads(request.body or "{}")
        name = data.get("name") or f"Config {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        loaded_ids = data.get("loaded_ids")

        if loaded_ids is None or not isinstance(loaded_ids, list):
            return JsonResponse({"success": False, "message": "Missing 'loaded_ids' list in request."}, status=400)
        

        with transaction.atomic():
            config = SavedConfiguration.objects.create(simulation=sim, name=name)

            # placements = SimPlacement.objects.filter(sim=sim).select_related("hu")
            placements = SimPlacement.objects.filter(
                sim=sim, 
                hu_id__in=loaded_ids  # Filter by handling unit ID (assuming 'hu' is the foreign key)
            ).select_related("hu")
            objs = []
            for p in placements:
                objs.append(SavedPlacement(
                    configuration=config,
                    handling_unit=p.hu,
                    x=p.x,
                    y=p.y,
                    z=p.z,
                    orientation=str(p.orientation)[-3:],
                ))
            # bulk create for speed
            if objs:
                SavedPlacement.objects.bulk_create(objs)

        return JsonResponse({"success": True, "message": f"Configuration '{name}' saved.", "config_id": config.id})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)





@require_http_methods(["GET"])
def list_configurations(request, simulation_id):
    """
    Return JSON list of saved configurations for a simulation.
    """
    try:
        configs = SavedConfiguration.objects.filter(simulation_id=simulation_id).order_by("-created_at")
        data = [
            {"id": c.id, "name": c.name, "created_at": c.created_at.isoformat()}
            for c in configs
        ]
        return JsonResponse({"success": True, "configs": data})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def load_configuration(request, config_id):
    """
    Replace this simulation's SimPlacement entries with placements from SavedConfiguration.
    """
    try:
        config = get_object_or_404(SavedConfiguration, id=config_id)
        sim = config.simulation

        with transaction.atomic():
            # delete current placements for this simulation
            SimPlacement.objects.filter(sim=sim).delete()

            # copy saved placements back into SimPlacement
            objs = []
            for sp in config.placements.select_related("handling_unit").all():
                objs.append(SimPlacement(
                    sim=sim,
                    hu=sp.handling_unit,
                    x=sp.x,
                    y=sp.y,
                    z=sp.z,
                    orientation=sp.orientation,
                    temp_remove=False
                ))
            if objs:
                SimPlacement.objects.bulk_create(objs)

        return JsonResponse({"success": True, "message": f"Configuration '{config.name}' loaded."})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_configuration(request, config_id):
    """
    Delete a saved configuration and its associated placements.
    """
    try:
        config = get_object_or_404(SavedConfiguration, id=config_id)
        config_name = config.name
        config.delete()
        return JsonResponse({"success": True, "message": f"Configuration '{config_name}' deleted."})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def set_restrictions(request):
    """
    Create or update a SimPlacement entry for an existing HandlingUnit.
    Expected JSON payload:
    {
        "id": "HU123",
        "no_stacking": True,
        "this_side_up": False
    }
    """
    try:
        data = json.loads(request.body)

        hu_id = data.get("id")

        if not hu_id:
            return JsonResponse({
                "success": False,
                "message": "Missing Handling Unit ID."
            }, status=400)

        # Check that the HU exists first
        hu_exists = HandlingUnit.objects.filter(id=hu_id).exists()
        if not hu_exists:
            return JsonResponse({
                "success": False,
                "message": f"Cannot set restrictions: Handling Unit ID '{hu_id}' does not exist."
            }, status=400)

        # Retrieve the actual instances
        hu = HandlingUnit.objects.get(id=hu_id)

        hu.restrictions = Restriction(0)
        if data.get("no_stacking"):
            hu.restrictions |= Restriction.NO_STACKING
        if data.get("this_side_up"):
            hu.restrictions |= Restriction.THIS_SIDE_UP
        hu.save()

        return JsonResponse({
            "success": True,
            "message": (
                f"Updated HU '{hu.id}'"
            ),
            "placement": {
                "hu": hu.id,
                "restrictions": hu.restrictions.value,
            }
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Error setting restrictions: {str(e)}"
        }, status=400)




@csrf_exempt
@require_http_methods(["POST"])
def set_sim_position(request):
    """
    Create or update a SimPlacement entry for an existing HandlingUnit.
    Expected JSON payload:
    {
        "id": "HU123",
        "simulation_id": 1,
        "x": 12.3,
        "y": 4.5,
        "z": -6.7,
        "orientation": "XYZ"   # optional
    }
    """
    try:
        data = json.loads(request.body)

        hu_id = data.get("id")
        sim_id = data.get("simulation_id")

        if not hu_id or not sim_id:
            return JsonResponse({
                "success": False,
                "message": "Missing Handling Unit ID or Simulation ID."
            }, status=400)

        # Check that the HU exists first
        hu_exists = HandlingUnit.objects.filter(id=hu_id).exists()
        if not hu_exists:
            return JsonResponse({
                "success": False,
                "message": f"Cannot set position: Handling Unit ID '{hu_id}' does not exist."
            }, status=400)

        # Retrieve the actual instances
        hu = HandlingUnit.objects.get(id=hu_id)
        sim = get_object_or_404(Simulation, id=sim_id)

        orientation = data.get("orientation", "XYZ")

        placement, created = SimPlacement.objects.update_or_create(
            hu=hu,
            sim=sim,
            defaults={
                "x": float(data.get("x_coord", 0)),
                "y": float(data.get("y_coord", 0)),
                "z": -float(data.get("z_coord", 0)),
                "orientation": orientation,
                "temp_remove": False
            }
        )

        return JsonResponse({
            "success": True,
            "message": (
                f"Position {'created' if created else 'updated'} "
                f"for HU '{hu.id}' in simulation {sim.id}."
            ),
            "placement": {
                "hu": hu.id,
                "x": placement.x,
                "y": placement.y,
                "z": placement.z,
                "orientation": str(placement.orientation),
                "simulation_id": sim.id
            }
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Error setting position: {str(e)}"
        }, status=400)




def get_simplacements(request):
    sim_id = request.GET.get('simulation_id')
    if not sim_id:
        return JsonResponse({'success': False, 'message': 'simulation_id required'})

    placements = SimPlacement.objects.filter(sim_id=sim_id).select_related('hu')

    data = []
    for p in placements:
        data.append({
            # 'id': p.item.id,
            'hu_id': p.hu_id,
            'dest_x_coord': p.x,
            'dest_y_coord': p.y,
            'dest_z_coord': p.z,
            # 'orientation': p.orientation,
            # 'x_size': p.item.x_size,
            # 'y_size': p.item.y_size,
            # 'z_size': p.item.z_size,
            # 'name': p.item.name,
        })

    return JsonResponse({'success': True, 'items': data})



@require_http_methods(["GET"])
def get_items(request):
    try:
        simulation_id = request.GET.get('simulation_id')

        if simulation_id:
            items = HandlingUnit.objects.filter(temp_add_id=simulation_id).values(
                'id', 'weight', 'x_size', 'y_size', 'z_size', 'shipment', 'stop', 'color'
            )
        else:
            items = HandlingUnit.objects.all().values(
                'id', 'weight', 'x_size', 'y_size', 'z_size', 'shipment', 'stop', 'color'
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

# Unused Function; commented out but kept for potential future use
# @csrf_exempt
# @require_http_methods(["POST"])
# def create_load(request):
#     try:
#         data = json.loads(request.body)
#         simulation = Simulation.objects.create(name=data['name'])
#         return JsonResponse({
#             'success': True,
#             'message': f'Load "{simulation.name}" created successfully!',
#             'simulation': {
#                 'id': simulation.id,
#                 'name': simulation.name,
#                 'time': simulation.time.isoformat()
#             }
#         })
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'message': f'Error creating load: {str(e)}'
#         }, status=400)

# Unused Function; commented out but kept for potential future use
# @csrf_exempt
# @require_http_methods(["POST"])
# def import_csv(request):
#     try:
#         simulation_id = request.POST.get('simulation_id')
#         csv_file = request.FILES.get('csv_file')

#         if not csv_file:
#             return JsonResponse({
#                 'success': False,
#                 'message': 'No CSV file provided'
#             }, status=400)

#         if not simulation_id:
#             return JsonResponse({
#                 'success': False,
#                 'message': 'No simulation ID provided'
#             }, status=400)

#         simulation = get_object_or_404(Simulation, id=simulation_id)

#         csv_data = csv_file.read().decode('utf-8-sig')  # utf-8-sig removes BOM
#         csv_reader = csv.DictReader(io.StringIO(csv_data))

#         items_created = 0
#         errors = []

#         for row in csv_reader:
#             try:
#                 shipment, _ = Shipment.objects.get_or_create(
#                     id=int(row['Shipment']),
#                     defaults={'name': f"Shipment {row['Shipment']}"}
#                 )

#                 HandlingUnit.objects.create(
#                     id=row['HU Number'],
#                     weight=float(row['Gross Weight']),
#                     x_size=float(row['Length']),
#                     y_size=float(row['Width']),
#                     z_size=float(row['Height']),
#                     shipment=shipment,
#                     stop=row['Stop'],
#                     temp_add=simulation
#                 )
#                 items_created += 1
#             except Exception as e:
#                 errors.append(f"Row {row.get('HU Number', 'unknown')}: {str(e)}")

#         return JsonResponse({
#             'success': True,
#             'message': f'Successfully imported {items_created} items',
#             'items_created': items_created,
#             'errors': errors
#         })
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'message': f'Error importing CSV: {str(e)}'
#         }, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def create_load_with_csv(request):
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


        csv_data = csv_file.read().decode('utf-8-sig')  # utf-8-sig removes BOM
        csv_reader = csv.DictReader(io.StringIO(csv_data))

        items_created = 0
        errors = []

        for row in csv_reader:
            try:
                shipment, _ = Shipment.objects.get_or_create(
                    id=int(row['Shipment']),
                    defaults={'name': f"Shipment {row['Shipment']}"}
                )

                simulation, _ = Simulation.objects.get_or_create(name=load_name, shipment=shipment)
                stop_value = (row.get('Stop') or '').strip()

                HandlingUnit.objects.create(
                    id=row['HU Number'],
                    weight=float(row['Gross Weight']),
                    x_size=float(row['Length']),
                    y_size=float(row['Width']),
                    z_size=float(row['Height']),
                    shipment=shipment,
                    stop=stop_value,
                    color=color_for_stop(stop_value),
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
            'message': 'Unable to create load. Please check your CSV file and try again.'
        }, status=400)
    
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_item(request, item_id):
    try:
        item = get_object_or_404(HandlingUnit, id=item_id)
        item.delete()
        return JsonResponse({
            'success': True,
            'message': f'Item {item_id} deleted successfully.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting item: {str(e)}'
        }, status=400)