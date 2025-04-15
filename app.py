from flask import Flask, request, jsonify, render_template
from flasgger import Swagger, swag_from
import sqlite3
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')

# Configuração do Swagger com template personalizado
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec_1',
            "route": '/apispec_1.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
    "title": "Incident Management API",
    "description": "API for managing incidents and affected services",
    "version": "1.0.0",
    "swagger_ui_bundle_js": "https://unpkg.com/swagger-ui-dist@3/swagger-ui-bundle.js",
    "swagger_ui_standalone_preset_js": "https://unpkg.com/swagger-ui-dist@3/swagger-ui-standalone-preset.js",
    "swagger_ui_css": "https://unpkg.com/swagger-ui-dist@3/swagger-ui.css",
    "swagger_ui_config": {
        "dom_id": "#swagger-ui",
        "styles": """
            .swagger-ui .info .description { display: none; } /* Opcional: oculta descrição */
            .swagger-ui .footer { display: none; } /* Oculta o footer */
        """
    }
}

template = {
    "swagger": "2.0",
    "info": {
        "title": "Incident Management API",
        "description": (
            "API for creating, updating, retrieving, and deleting incidents and their affected services. "
        ),
        "version": "1.0.0"
    },
    "schemes": ["http", "https"],
    "tags": [
        {"name": "Incidents", "description": "Operations related to incidents"},
        {"name": "Services", "description": "Operations related to affected services"}
    ],
    "securityDefinitions": {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-KEY"
        }
    }
}

swagger = Swagger(app, config=swagger_config, template=template)

db_file = 'incidents.db'

def create_database():
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            element TEXT NOT NULL,
            issue_type TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT,
            time_range TEXT NOT NULL,
            type_service TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS affected_services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id INTEGER,
            service_id TEXT NOT NULL,
            FOREIGN KEY (incident_id) REFERENCES incidents(id)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_service_id ON affected_services(service_id)')
    conn.commit()
    conn.close()

create_database()

def get_incidents_data():
    # Connect to the database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    try:
        # Fetch all incidents with their affected services
        cursor.execute('''
            SELECT i.id, i.element, i.issue_type, i.start_date, i.end_date, i.time_range, i.type_service, a.service_id
            FROM incidents i
            LEFT JOIN affected_services a ON i.id = a.incident_id
        ''')
        results = cursor.fetchall()
        incidents = {}
        for row in results:
            incident_id = row[0]
            if incident_id not in incidents:
                incidents[incident_id] = {
                    "id": incident_id,
                    "element": row[1],
                    "issue_type": row[2],
                    "start_date": row[3],
                    "end_date": row[4],
                    "time_range": row[5],
                    "type_service": row[6],
                    "services_affected": []
                }
            if row[7]:
                incidents[incident_id]["services_affected"].append(row[7])
        return list(incidents.values())
    except Exception as e:
        raise Exception(str(e))
    finally:
        conn.close()

def get_incident_by_service_id(service_id):
    # Connect to the database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    try:
        # Fetch incident details by service ID
        cursor.execute('''
            SELECT i.element, i.issue_type, i.start_date, i.end_date, i.time_range, i.type_service, a.service_id
            FROM incidents i
            JOIN affected_services a ON i.id = a.incident_id
            WHERE a.service_id = ?
        ''', (service_id,))
        result = cursor.fetchone()
        if result:
            return {
                "element": result[0],
                "issue_type": result[1],
                "start_date": result[2],
                "end_date": result[3],
                "time_range": result[4],
                "type_service": result[5],
                "service_id": result[6]
            }
        return None
    except Exception as e:
        raise Exception(str(e))
    finally:
        conn.close()

def get_id_incident_by_element(element_name):
    # Connect to the database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    try:
        # Fetch all incident details by element name
        cursor.execute('''
            SELECT i.id, i.element, i.issue_type, i.start_date, i.end_date, i.time_range, i.type_service
            FROM incidents i
            WHERE i.element = ?
        ''', (element_name,))
        incident = cursor.fetchone()
        
        if not incident:
            return None
        
        # Fetch associated affected services
        cursor.execute('''
            SELECT service_id
            FROM affected_services
            WHERE incident_id = ?
        ''', (incident[0],))
        services = [row[0] for row in cursor.fetchall()]
        
        # Construct the response dictionary
        result = {
            "id": incident[0],
            "element": incident[1],
            "issue_type": incident[2],
            "start_date": incident[3],
            "end_date": incident[4],
            "time_range": incident[5],
            "type_service": incident[6],
            "services_affected": services
        }
        
        return result
    except Exception as e:
        raise Exception(str(e))
    finally:
        conn.close()


# Rotas da API com documentação Swagger
@app.route('/', methods=['GET'])
def home():
    """Renderiza a página inicial."""
    return render_template('home.html')

@app.route('/incidents', methods=['GET'])
@swag_from({
    'tags': ['Incidents'],
    'summary': 'Retrieve all incidents',
    'description': 'Returns a list of all incidents with their affected services.',
    'responses': {
        200: {
            'description': 'List of incidents',
            'schema': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'integer'},
                        'element': {'type': 'string'},
                        'issue_type': {'type': 'string'},
                        'start_date': {'type': 'string'},
                        'end_date': {'type': 'string'},
                        'time_range': {'type': 'string'},
                        'type_service': {'type': 'string'},
                        'services_affected': {'type': 'array', 'items': {'type': 'string'}}
                    }
                }
            }
        },
        404: {
            'description': 'No incidents found'
        },
        500: {
            'description': 'Internal server error'
        }
    }
})
def get_incidents():
    try:
        data = get_incidents_data()
        if not data:
            return jsonify({"error": "No incidents found"}), 404
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/incidents/service/<service_id>', methods=['GET'])
@swag_from({
    'tags': ['Services'],
    'summary': 'Get incident by service ID',
    'description': 'Returns the incident associated with the given service ID.',
    'parameters': [
        {
            'name': 'service_id',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'The ID of the service to query'
        }
    ],
    'responses': {
        200: {
            'description': 'Incident details',
            'schema': {
                'type': 'object',
                'properties': {
                    'element': {'type': 'string'},
                    'issue_type': {'type': 'string'},
                    'start_date': {'type': 'string'},
                    'end_date': {'type': 'string'},
                    'time_range': {'type': 'string'},
                    'type_service': {'type': 'string'},
                    'service_id': {'type': 'string'}
                }
            }
        },
        404: {
            'description': 'Incident not found for this service ID'
        },
        500: {
            'description': 'Internal server error'
        }
    }
})
def get_incident_service(service_id):
    try:
        data = get_incident_by_service_id(service_id)
        if not data:
            return jsonify({"error": "Incident not found for this service ID"}), 404
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/incidents/element/<element_name>', methods=['GET'])
@swag_from({
    'tags': ['Incidents'],
    'summary': 'Get incident ID by element name',
    'description': 'Returns the ID of the incident associated with the given element name.',
    'parameters': [
        {
            'name': 'element_name',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'The name of the element to query'
        }
    ],
    'responses': {
        200: {
            'description': 'Incident ID',
            'schema': {
                'type': 'object',
                'properties': {
                    'incident_id': {'type': 'integer'}
                }
            }
        },
        404: {
            'description': 'Incident not found for this element'
        },
        500: {
            'description': 'Internal server error'
        }
    }
})
def get_incident_element(element_name):
    try:
        data = get_id_incident_by_element(element_name)
        if not data:
            return jsonify({"error": "Incident not found for this element"}), 404
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/incidents/create/', methods=['POST'])
@swag_from({
    'tags': ['Incidents'],
    'summary': 'Create a new incident',
    'description': 'Creates a new incident with the provided details and affected services.',
    'consumes': ['application/json'],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'element': {'type': 'string', 'example': 'Server A'},
                    'issue_type': {'type': 'string', 'example': 'Outage'},
                    'start_date': {'type': 'string', 'example': '01-01-2023 10:00'},
                    'end_date': {'type': 'string', 'example': '01-01-2023 12:00'},
                    'type_service': {'type': 'string', 'example': 'Web Service'},
                    'services_affected': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'example': ['svc1', 'svc2']
                    }
                },
                'required': ['element', 'issue_type', 'start_date', 'type_service', 'services_affected']
            }
        }
    ],
    'responses': {
        201: {
            'description': 'Incident created successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'incident_id': {'type': 'integer'},
                    'message': {'type': 'string'}
                }
            }
        },
        400: {
            'description': 'Invalid or missing data'
        },
        415: {
            'description': 'Unsupported media type'
        },
        500: {
            'description': 'Internal server error'
        }
    }
})
def create_incident():
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid data"}), 415

        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        required_fields = ["element", "issue_type", "start_date", "type_service", "services_affected"]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        incident_id = insert_database(
            element=data["element"],
            issue_type=data["issue_type"],
            start_date=data["start_date"],
            end_date=data.get("end_date"),
            type_service=data["type_service"],
            services_affected=data["services_affected"]
        )
        return jsonify({"incident_id": incident_id, "message": "Incident created successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/incidents/update/', methods=['POST'])
@swag_from({
    'tags': ['Incidents'],
    'summary': 'Update an existing incident',
    'description': 'Updates an incident with the provided details. Only provided fields are updated.',
    'consumes': ['application/json'],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'incident_id': {'type': 'integer', 'example': 1},
                    'element': {'type': 'string', 'example': 'Server B'},
                    'issue_type': {'type': 'string', 'example': 'Performance'},
                    'start_date': {'type': 'string', 'example': '02-01-2023 08:00'},
                    'end_date': {'type': 'string', 'example': '02-01-2023 09:00'},
                    'type_service': {'type': 'string', 'example': 'Database'},
                    'services_affected': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'example': ['svc3']
                    }
                },
                'required': ['incident_id']
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Incident updated successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'}
                }
            }
        },
        400: {
            'description': 'Invalid or missing data'
        },
        404: {
            'description': 'Incident not found'
        },
        415: {
            'description': 'Unsupported media type'
        },
        500: {
            'description': 'Internal server error'
        }
    }
})
def update_incident():
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid data"}), 415
        
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        if "incident_id" not in data:
            return jsonify({"error": "Invalid data - incident_id"}), 415    
        incident_id = data["incident_id"]
        success = update_database(
            incident_id=incident_id,
            element=data.get("element"),
            issue_type=data.get("issue_type"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            type_service=data.get("type_service"),
            services_affected=data.get("services_affected")
        )
        if not success:
            return jsonify({"error": "Incident not found"}), 404
        return jsonify({"message": "Incident updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/incidents/html', methods=['GET'])
@swag_from({
    'tags': ['Incidents'],
    'summary': 'Render incidents as HTML',
    'description': 'Returns an HTML page displaying all incidents.',
    'responses': {
        200: {
            'description': 'HTML page with incidents'
        },
        500: {
            'description': 'Internal server error'
        }
    }
})
def get_incidents_html():
    try:
        data = get_incidents_data()
        return render_template('incidents.html', incidents=data)
    except Exception as e:
        return f"Error: {str(e)}", 500


@app.route('/incidents/delete/<int:incident_id>', methods=['DELETE'])
@swag_from({
    'tags': ['Incidents'],
    'summary': 'Delete an incident',
    'description': 'Deletes an incident and its associated affected services by incident ID.',
    'parameters': [
        {
            'name': 'incident_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': 'The ID of the incident to delete'
        }
    ],
    'responses': {
        200: {
            'description': 'Incident deleted successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'}
                }
            }
        },
        404: {
            'description': 'Incident not found'
        },
        500: {
            'description': 'Internal server error'
        }
    }
})
def delete_incident_route(incident_id):
    try:
        success = delete_incident(incident_id)
        if not success:
            return jsonify({"error": "Incident not found"}), 404
        return jsonify({"message": "Incident and its affected services deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
