from flask import Flask, request, jsonify, render_template
from flasgger import Swagger, swag_from
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Index, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import select, join
from sqlalchemy.sql import text

from datetime import datetime
from dotenv import load_dotenv
import os

app = Flask(__name__, template_folder='templates', static_folder='static')

# Configuração do Swagger (permanece inalterada)
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
            .swagger-ui .info .description { display: none; }
            .swagger-ui .footer { display: none; }
        """
    }
}

template = {
    "swagger": "2.0",
    "info": {
        "title": "Incident Management API",
        "description": (
            "API for retrieving incidents and their affected services. "
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

# Configuração do SQLAlchemy
load_dotenv()

DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DB_URL = f"postgresql+psycopg2://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
print(DB_URL)
Base = declarative_base()

# Modelos
class Incident(Base):
    __tablename__ = 'incidents'
    __table_args__ = {'schema': 'network'}
    
    id = Column(Integer, primary_key=True)
    element = Column(String, nullable=False)
    issue_type = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    time_range = Column(String, nullable=False)
    type_service = Column(String, nullable=False)
    affected_services = relationship("AffectedService", back_populates="incident")

class AffectedService(Base):
    __tablename__ = 'affected_services'
    __table_args__ = {'schema': 'network'}  # Especifica o schema
    
    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey('network.incidents.id'))  # Referencia o schema
    service_id = Column(String, nullable=False)
    incident = relationship("Incident", back_populates="affected_services")

Index('idx_service_id', AffectedService.service_id)

class HistoricIncident(Base):
    __tablename__ = 'historic_incidents'
    __table_args__ = {'schema': 'network'}  # Especifica o schema
    
    id = Column(Integer, primary_key=True)
    element = Column(String, nullable=False)
    issue_type = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    time_range = Column(String, nullable=False)
    type_service = Column(String, nullable=False)

def connect_database():
    try:
        engine = create_engine(DB_URL)
        Session = sessionmaker(bind=engine)
        Base.metadata.create_all(engine)
        return Session, engine
    except Exception as e:
        raise Exception(f"Erro ao configurar o banco de dados: {e}")    

# Criação das tabelas
def create_database():
    Session, engine = connect_database()
    session = Session()
    try:
        Base.metadata.create_all(engine)
        print("Tabelas criadas com sucesso no schema 'network'!")
    except Exception as e:
        print(f"Erro ao criar tabelas: {e}")
        raise
    finally:
        session.close()
#create_database()

def get_incidents_data():
    Session, _ = connect_database()
    session = Session()
    try:
        # Fetch all incidents with their affected services
        results = (session.query(Incident, AffectedService)
                   .outerjoin(AffectedService, Incident.id == AffectedService.incident_id)
                   .all())
        
        incidents = {}
        for incident, affected_service in results:
            incident_id = incident.id
            if incident_id not in incidents:
                incidents[incident_id] = {
                    "id": incident_id,
                    "element": incident.element,
                    "issue_type": incident.issue_type,
                    "start_date": incident.start_date,
                    "end_date": incident.end_date,
                    "time_range": incident.time_range,
                    "type_service": incident.type_service,
                    "services_affected": []
                }
            if affected_service and affected_service.service_id:
                incidents[incident_id]["services_affected"].append(affected_service.service_id)
        return list(incidents.values())
    except Exception as e:
        raise Exception(str(e))
    finally:
        session.close()

def get_incident_by_service_id(service_id):
    Session, _ = connect_database()
    session = Session()
    try:
        result = (session.query(Incident, AffectedService)
                  .join(AffectedService, Incident.id == AffectedService.incident_id)
                  .filter(AffectedService.service_id == service_id)
                  .first())
        if result:
            incident, affected_service = result
            return {
                "element": incident.element,
                "issue_type": incident.issue_type,
                "start_date": incident.start_date,
                "end_date": incident.end_date,
                "time_range": incident.time_range,
                "type_service": incident.type_service,
                "service_id": affected_service.service_id
            }
        return None
    except Exception as e:
        raise Exception(str(e))
    finally:
        session.close()

def get_id_incident_by_element(element_name):
    Session, _ = connect_database()
    session = Session()
    try:
        incident = session.query(Incident).filter(Incident.element == element_name).first()
        if not incident:
            return None
        
        services = [service.service_id for service in incident.affected_services]
        
        result = {
            "id": incident.id,
            "element": incident.element,
            "issue_type": incident.issue_type,
            "start_date": incident.start_date,
            "end_date": incident.end_date,
            "time_range": incident.time_range,
            "type_service": incident.type_service,
            "services_affected": services
        }
        return result
    except Exception as e:
        raise Exception(str(e))
    finally:
        session.close()

def insert_database(element, issue_type, start_date, end_date, type_service, services_affected):
    Session, _ = connect_database()
    session = Session()
    try:
        time_range = f"{start_date} - {end_date or 'ongoing'}"
        incident = Incident(
            element=element,
            issue_type=issue_type,
            start_date=start_date,
            end_date=end_date,
            time_range=time_range,
            type_service=type_service
        )
        session.add(incident)
        session.flush()  # Garante que o ID do incidente seja gerado
        
        for service_id in services_affected:
            affected_service = AffectedService(incident_id=incident.id, service_id=service_id)
            session.add(affected_service)
        
        session.commit()
        return incident.id
    except Exception as e:
        session.rollback()
        raise Exception(str(e))
    finally:
        session.close()

def update_database(incident_id, element=None, issue_type=None, start_date=None, end_date=None, type_service=None, services_affected=None):
    Session, _ = connect_database()
    session = Session()
    try:
        incident = session.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return False
        
        if element:
            incident.element = element
        if issue_type:
            incident.issue_type = issue_type
        if start_date:
            incident.start_date = start_date
        if end_date:
            incident.end_date = end_date
        if type_service:
            incident.type_service = type_service
        if start_date or end_date:
            incident.time_range = f"{start_date or incident.start_date} - {end_date or 'ongoing'}"
        
        if services_affected is not None:
            session.query(AffectedService).filter(AffectedService.incident_id == incident_id).delete()
            for service_id in services_affected:
                session.add(AffectedService(incident_id=incident_id, service_id=service_id))
        
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise Exception(str(e))
    finally:
        session.close()

def delete_incident(incident_id):
    Session, _ = connect_database()
    session = Session()
    try:
        incident = session.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return False
        
        session.delete(incident)  # Cascade delete removerá os affected_services
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise Exception(str(e))
    finally:
        session.close()

# Rotas da API 
@app.route('/', methods=['GET'])
def home():
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
# @swag_from({
#     'tags': ['Incidents'],
#     'summary': 'Create a new incident',
#     'description': 'Creates a new incident with the provided details and affected services.',
#     'consumes': ['application/json'],
#     'parameters': [
#         {
#             'name': 'body',
#             'in': 'body',
#             'required': True,
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'element': {'type': 'string', 'example': 'Server A'},
#                     'issue_type': {'type': 'string', 'example': 'Outage'},
#                     'start_date': {'type': 'string', 'example': '01-01-2023 10:00'},
#                     'end_date': {'type': 'string', 'example': '01-01-2023 12:00'},
#                     'type_service': {'type': 'string', 'example': 'Web Service'},
#                     'services_affected': {
#                         'type': 'array',
#                         'items': {'type': 'string'},
#                         'example': ['svc1', 'svc2']
#                     }
#                 },
#                 'required': ['element', 'issue_type', 'start_date', 'type_service', 'services_affected']
#             }
#         }
#     ],
#     'responses': {
#         201: {
#             'description': 'Incident created successfully',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'incident_id': {'type': 'integer'},
#                     'message': {'type': 'string'}
#                 }
#             }
#         },
#         400: {
#             'description': 'Invalid or missing data'
#         },
#         415: {
#             'description': 'Unsupported media type'
#         },
#         500: {
#             'description': 'Internal server error'
#         }
#     }
# })
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
# @swag_from({
#     'tags': ['Incidents'],
#     'summary': 'Update an existing incident',
#     'description': 'Updates an incident with the provided details. Only provided fields are updated.',
#     'consumes': ['application/json'],
#     'parameters': [
#         {
#             'name': 'body',
#             'in': 'body',
#             'required': True,
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'incident_id': {'type': 'integer', 'example': 1},
#                     'element': {'type': 'string', 'example': 'Server B'},
#                     'issue_type': {'type': 'string', 'example': 'Performance'},
#                     'start_date': {'type': 'string', 'example': '02-01-2023 08:00'},
#                     'end_date': {'type': 'string', 'example': '02-01-2023 09:00'},
#                     'type_service': {'type': 'string', 'example': 'Database'},
#                     'services_affected': {
#                         'type': 'array',
#                         'items': {'type': 'string'},
#                         'example': ['svc3']
#                     }
#                 },
#                 'required': ['incident_id']
#             }
#         }
#     ],
#     'responses': {
#         200: {
#             'description': 'Incident updated successfully',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'message': {'type': 'string'}
#                 }
#             }
#         },
#         400: {
#             'description': 'Invalid or missing data'
#         },
#         404: {
#             'description': 'Incident not found'
#         },
#         415: {
#             'description': 'Unsupported media type'
#         },
#         500: {
#             'description': 'Internal server error'
#         }
#     }
# })
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
# @swag_from({
#     'tags': ['Incidents'],
#     'summary': 'Delete an incident',
#     'description': 'Deletes an incident and its associated affected services by incident ID.',
#     'parameters': [
#         {
#             'name': 'incident_id',
#             'in': 'path',
#             'type': 'integer',
#             'required': True,
#             'description': 'The ID of the incident to delete'
#         }
#     ],
#     'responses': {
#         200: {
#             'description': 'Incident deleted successfully',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'message': {'type': 'string'}
#                 }
#             }
#         },
#         404: {
#             'description': 'Incident not found'
#         },
#         500: {
#             'description': 'Internal server error'
#         }
#     }
# })
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
