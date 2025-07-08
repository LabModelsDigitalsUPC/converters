"""
Compact IFC Converter - Complete IFC to RDF + GLB conversion
Author: Assistant
Description: Self-contained converter for IFC files to RDF metadata and GLB geometry
"""
#workflow test comment 1

import ifcopenshell
import ifcopenshell.geom
from rdflib import Graph, Namespace, Literal, URIRef
import json
import pathlib
import os
import logging
import numpy as np
from pygltflib import GLTF2, Scene, Node, Mesh, Primitive, Accessor, BufferView, Buffer, Material, PbrMetallicRoughness
import uuid
from typing import Dict, Optional, List, Tuple, Any
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class CompactIFCConverter:
    """Compact IFC converter with external conversion map configuration"""
    
    # Default color mapping by IFC type
    DEFAULT_COLORS = {
        'IfcWall': (0.8, 0.8, 0.8, 1.0),
        'IfcSlab': (0.7, 0.7, 0.7, 1.0),
        'IfcColumn': (0.6, 0.6, 0.9, 1.0),
        'IfcBeam': (0.9, 0.6, 0.6, 1.0),
        'IfcDoor': (0.8, 0.5, 0.2, 1.0),
        'IfcWindow': (0.5, 0.8, 0.9, 1.0),
        'IfcStair': (0.7, 0.8, 0.6, 1.0),
        'IfcRoof': (0.8, 0.4, 0.4, 1.0),
        'IfcRailing': (0.5, 0.5, 0.5, 1.0),
        'default': (0.5, 0.5, 0.5, 1.0)
    }
    
    def __init__(self, 
                 ifc_file_path: str,
                 asset_name: Optional[str] = None,
                 base_url: str = "http://localhost:8000/data/",
                 rdf_output_path: str = "./data/rdf",
                 glb_output_path: str = "./data/glb",
                 convert_geometry: bool = True,
                 conversion_map_path: Optional[str] = None):
        """
        Initialize compact IFC converter
        
        Args:
            ifc_file_path: Path to IFC file
            asset_name: Name for output files (auto-generated if None)
            base_url: Base URL for RDF namespaces
            rdf_output_path: Directory for RDF output
            glb_output_path: Directory for GLB output
            convert_geometry: Whether to generate GLB file
            conversion_map_path: Path to conversion-map.json file
        """
        
        # Configuration
        self.ifc_file_path = ifc_file_path
        self.asset_name = asset_name or pathlib.Path(ifc_file_path).stem
        self.base_url = base_url if base_url.endswith('/') else base_url + '/'
        self.rdf_output_path = rdf_output_path
        self.glb_output_path = glb_output_path
        self.convert_geometry = convert_geometry
        
        # Load conversion map
        self.conversion_map = self._load_conversion_map(conversion_map_path)
        
        # IFC processing
        self.ifc_file = None
        self.schema = None
        self.settings = None
        
        # GLB processing
        self.elements_data = []
        self.binary_data = bytearray()
        self.materials_map = {}
        
        # RDF processing
        self.graph = Graph()
        self.created_entities = {}
        self.properties_cache = {}
        self.type_maps = {}
        
        # Results
        self.conversion_results = {
            'success': False,
            'files': {},
            'metadata': {},
            'errors': []
        }
        
        self._setup_namespaces()
        logger.info(f"CompactIFCConverter initialized for: {self.asset_name}")
    
    def _load_conversion_map(self, conversion_map_path: Optional[str] = None) -> Dict:
        """Load conversion map from external JSON file"""
        # Determine conversion map path
        if conversion_map_path:
            map_path = pathlib.Path(conversion_map_path)
        else:
            # Look for conversion-map.json in the same directory as this script
            script_dir = pathlib.Path(__file__).parent
            map_path = script_dir / 'conversion-map.json'

        # Use resource_path to support PyInstaller bundles. (for github actions)
        map_path_str = str(map_path)
        if getattr(sys, 'frozen', False):
            # If running in a bundle
            map_path_str = resource_path(str(map_path.relative_to(pathlib.Path(__file__).parent.parent)))
        try:
            logger.info(f"Loading conversion map from: {map_path_str}")
            with open(map_path_str, 'r', encoding='utf-8') as f:
                conversion_map = json.load(f)
            logger.info(f"Conversion map loaded successfully")
            return conversion_map

        except Exception as e:
            logger.error(f"Error loading conversion map from {map_path_str}: {e}")
            logger.warning("Using minimal default mapping")
    
    def _setup_namespaces(self):
        """Setup RDF namespaces"""
        self.namespaces = {
            'INST': Namespace(self.base_url),
            'BEO': Namespace("https://w3id.org/beo#"),
            'OMG': Namespace("https://w3id.org/omg#"),
            'FOG': Namespace("https://w3id.org/fog#"),
            'GOM': Namespace("https://w3id.org/gom#"),
            'BOT': Namespace("https://w3id.org/bot#"),
            'XSD': Namespace("http://www.w3.org/2001/XMLSchema#"),
            'RDF': Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
            'RDFS': Namespace("http://www.w3.org/2000/01/rdf-schema#"),
            'OWL': Namespace("http://www.w3.org/2002/07/owl#")
        }
        
        # Bind prefixes
        for prefix, namespace in self.namespaces.items():
            self.graph.bind(prefix.lower(), namespace)
        
        # Add ontology declaration
        asset_ref = URIRef(self.base_url)
        self.graph.add((asset_ref, self.namespaces['RDF'].type, self.namespaces['OWL'].Ontology))
    
    def _generate_global_id(self) -> str:
        """Generate IFC-style GlobalId"""
        return str(uuid.uuid4())
    
    def _get_instance_uri(self, entity) -> Tuple[URIRef, str]:
        """Get instance URI using GlobalId or generate new one"""
        global_id = getattr(entity, 'GlobalId', None)
        if not global_id or not global_id.strip():
            global_id = self._generate_global_id()
        else:
            global_id = ifcopenshell.guid.split(ifcopenshell.guid.expand(global_id))
        return self.namespaces['INST'][global_id], global_id
    
    def load_ifc(self) -> bool:
        """Load and setup IFC file"""
        try:
            if not os.path.exists(self.ifc_file_path):
                raise FileNotFoundError(f"IFC file not found: {self.ifc_file_path}")
            
            logger.info(f"Loading IFC file: {self.ifc_file_path}")
            self.ifc_file = ifcopenshell.open(self.ifc_file_path)
            self.schema = ifcopenshell.ifcopenshell_wrapper.schema_by_name(self.ifc_file.schema)
            
            # Setup geometry settings
            self.settings = ifcopenshell.geom.settings()
            self.settings.set(self.settings.USE_WORLD_COORDS, True)
            self.settings.set(self.settings.WELD_VERTICES, True)
            
            logger.info(f"IFC loaded successfully. Schema: {self.ifc_file.schema}")
            return True
            
        except Exception as e:
            error_msg = f"Error loading IFC file: {e}"
            logger.error(error_msg)
            self.conversion_results['errors'].append(error_msg)
            return False
    
    def _cache_properties(self):
        """Cache properties and quantity sets"""
        logger.info("Caching IFC properties...")
        
        try:
            p_rels = self.ifc_file.by_type('IfcRelDefinesByProperties')
            
            for rel in p_rels:
                try:
                    p = rel.RelatingPropertyDefinition
                    property_data = {"name": getattr(p, 'Name', '')}
                    
                    # Process quantities and properties
                    if p.is_a('IfcElementQuantity'):
                        for quantity in getattr(p, 'Quantities', []):
                            qty_type = quantity.is_a()
                            if qty_type == 'IfcQuantityArea' and hasattr(quantity, 'AreaValue'):
                                property_data[quantity.Name] = quantity.AreaValue
                            elif qty_type == 'IfcQuantityLength' and hasattr(quantity, 'LengthValue'):
                                property_data[quantity.Name] = quantity.LengthValue
                            elif qty_type == 'IfcQuantityVolume' and hasattr(quantity, 'VolumeValue'):
                                property_data[quantity.Name] = quantity.VolumeValue
                    
                    elif p.is_a('IfcPropertySet'):
                        for prop in getattr(p, 'HasProperties', []):
                            try:
                                if hasattr(prop, 'Name') and hasattr(prop, 'NominalValue'):
                                    property_data[prop.Name] = prop.NominalValue.wrappedValue
                            except:
                                continue
                    
                    # Cache for related objects
                    for obj in rel.RelatedObjects:
                        global_id = getattr(obj, 'GlobalId', None)
                        if global_id:
                            if global_id not in self.properties_cache:
                                self.properties_cache[global_id] = {'psets': [], 'qsets': []}
                            
                            if p.is_a('IfcElementQuantity'):
                                self.properties_cache[global_id]['qsets'].append(property_data)
                            elif p.is_a('IfcPropertySet'):
                                self.properties_cache[global_id]['psets'].append(property_data)
                
                except Exception as e:
                    logger.debug(f"Error processing property: {e}")
                    continue
            
            logger.info(f"Properties cached for {len(self.properties_cache)} objects")
            
        except Exception as e:
            logger.warning(f"Error caching properties: {e}")
    
    def get_element_color(self, element) -> Tuple[float, float, float, float]:
        """Get color for element"""
        element_type = element.is_a()
        return self.DEFAULT_COLORS.get(element_type, self.DEFAULT_COLORS['default'])
    
    def process_geometry(self) -> bool:
        """Process geometry for GLB conversion"""
        if not self.convert_geometry:
            return True
        
        logger.info("Processing geometry for GLB conversion...")
        
        try:
            elements = self.ifc_file.by_type('IfcProduct')
            processed_count = 0
            
            for element in elements:
                try:
                    if not hasattr(element, 'Representation') or not element.Representation:
                        continue
                    
                    representations = element.Representation.Representations
                    
                    for rep_index, representation in enumerate(representations):
                        try:
                            shape = ifcopenshell.geom.create_shape(self.settings, element, representation)
                            
                            if shape and shape.geometry:
                                vertices = np.array(shape.geometry.verts).reshape((-1, 3))
                                faces = np.array(shape.geometry.faces).reshape((-1, 3))
                                
                                # Convert coordinates IFC (Z-up) to GLB (Y-up)
                                vertices_converted = vertices.copy()
                                vertices_converted[:, [1, 2]] = vertices_converted[:, [2, 1]]
                                vertices_converted[:, 2] = -vertices_converted[:, 2]
                                
                                if len(vertices_converted) > 0 and len(faces) > 0:
                                    color = self.get_element_color(element)
                                    material_index = self._get_or_create_material(color)
                                    
                                    _, global_id = self._get_instance_uri(element)
                                    
                                    element_data = {
                                        'name': f"{global_id}_{rep_index}" if len(representations) > 1 else global_id,
                                        'vertices': vertices_converted,
                                        'faces': faces,
                                        'material_index': material_index,
                                        'color': color,
                                        'global_id': global_id,
                                        'element_type': element.is_a(),
                                        'element_id': element.id(),
                                        'representation_index': rep_index,
                                        'vertex_count': len(vertices_converted),
                                        'face_count': len(faces)
                                    }
                                    
                                    self.elements_data.append(element_data)
                                    processed_count += 1
                        
                        except Exception as e:
                            logger.debug(f"Error processing representation: {e}")
                            continue
                
                except Exception as e:
                    logger.debug(f"Error processing element {element.id()}: {e}")
                    continue
            
            logger.info(f"Geometry processed: {processed_count} representations")
            return processed_count > 0
            
        except Exception as e:
            error_msg = f"Error processing geometry: {e}"
            logger.error(error_msg)
            self.conversion_results['errors'].append(error_msg)
            return False
    
    def _get_or_create_material(self, color: Tuple[float, float, float, float]) -> int:
        """Get or create material index for color"""
        color_key = tuple(color)
        if color_key not in self.materials_map:
            self.materials_map[color_key] = len(self.materials_map)
        return self.materials_map[color_key]
    
    def _add_binary_data(self, data) -> Tuple[int, int]:
        """Add data to binary buffer with alignment"""
        if isinstance(data, np.ndarray):
            binary_data = data.astype(np.float32 if data.dtype != np.uint16 else np.uint16).tobytes()
        else:
            binary_data = data
        
        # 4-byte alignment
        while len(self.binary_data) % 4 != 0:
            self.binary_data.append(0)
        
        byte_offset = len(self.binary_data)
        self.binary_data.extend(binary_data)
        
        return byte_offset, len(binary_data)
    
    def create_glb(self) -> Optional[str]:
        """Create GLB file"""
        if not self.convert_geometry or not self.elements_data:
            return None
        
        try:
            logger.info(f"Creating GLB with {len(self.elements_data)} elements...")
            
            gltf = GLTF2()
            gltf.scenes = []
            gltf.nodes = []
            gltf.meshes = []
            gltf.materials = []
            gltf.accessors = []
            gltf.bufferViews = []
            gltf.buffers = []
            
            # Create materials
            for color, material_index in self.materials_map.items():
                material = Material()
                material.pbrMetallicRoughness = PbrMetallicRoughness()
                material.pbrMetallicRoughness.baseColorFactor = list(color)
                material.pbrMetallicRoughness.metallicFactor = 0.0
                material.pbrMetallicRoughness.roughnessFactor = 0.8
                material.name = f"Material_{material_index}"
                gltf.materials.append(material)
            
            # Process elements
            node_indices = []
            
            for element_data in self.elements_data:
                vertices = element_data['vertices']
                faces = element_data['faces'].flatten().astype(np.uint16)
                material_index = element_data['material_index']
                
                # Add to binary buffer
                vertex_offset, vertex_length = self._add_binary_data(vertices)
                index_offset, index_length = self._add_binary_data(faces)
                
                # Create buffer views and accessors
                vertex_buffer_view = BufferView(buffer=0, byteOffset=vertex_offset, byteLength=vertex_length, target=34962)
                index_buffer_view = BufferView(buffer=0, byteOffset=index_offset, byteLength=index_length, target=34963)
                
                gltf.bufferViews.extend([vertex_buffer_view, index_buffer_view])
                
                vertex_accessor = Accessor(
                    bufferView=len(gltf.bufferViews) - 2,
                    componentType=5126, count=len(vertices), type="VEC3",
                    min=vertices.min(axis=0).tolist(), max=vertices.max(axis=0).tolist()
                )
                index_accessor = Accessor(
                    bufferView=len(gltf.bufferViews) - 1,
                    componentType=5123, count=len(faces), type="SCALAR"
                )
                
                gltf.accessors.extend([vertex_accessor, index_accessor])
                
                # Create primitive, mesh, and node
                primitive = Primitive(
                    attributes={"POSITION": len(gltf.accessors) - 2},
                    indices=len(gltf.accessors) - 1,
                    material=material_index
                )
                
                mesh = Mesh(primitives=[primitive], name=element_data['name'])
                node = Node(mesh=len(gltf.meshes), name=element_data['name'])
                
                gltf.meshes.append(mesh)
                gltf.nodes.append(node)
                node_indices.append(len(gltf.nodes) - 1)
            
            # Create buffer and scene
            buffer = Buffer(byteLength=len(self.binary_data))
            gltf.buffers.append(buffer)
            
            scene = Scene(nodes=node_indices, name="IFC_Scene")
            gltf.scenes.append(scene)
            gltf.scene = 0
            
            # Save GLB
            os.makedirs(self.glb_output_path, exist_ok=True)
            glb_file_path = os.path.join(self.glb_output_path, f"{self.asset_name}.glb")
            
            gltf.set_binary_blob(bytes(self.binary_data))
            gltf.save(glb_file_path)
            
            logger.info(f"GLB created: {glb_file_path}")
            return glb_file_path
            
        except Exception as e:
            error_msg = f"Error creating GLB: {e}"
            logger.error(error_msg)
            self.conversion_results['errors'].append(error_msg)
            return None
    
    def create_rdf_entities(self):
        """Create RDF entities and relationships"""
        logger.info("Creating RDF entities...")
        
        try:
            processed_count = 0
            
            for entity in self.ifc_file:
                entity_type = entity.is_a()
                
                if entity_type in self.conversion_map['classes']:
                    try:
                        instance_uri, global_id = self._get_instance_uri(entity)
                        
                        if instance_uri not in self.created_entities:
                            self.created_entities[instance_uri] = True
                            
                            # Add entity types
                            class_uris = self.conversion_map['classes'][entity_type]['class']
                            for class_uri in class_uris:
                                self.graph.add((instance_uri, self.namespaces['RDF'].type, URIRef(class_uri)))
                            
                            # Add basic properties if available
                            if hasattr(entity, 'Name') and entity.Name:
                                self.graph.add((instance_uri, self.namespaces['RDFS'].label, 
                                              Literal(entity.Name, datatype=self.namespaces['XSD'].string)))
                            
                            # Add properties and quantities from cache
                            self._add_cached_properties(entity, instance_uri, global_id)
                            
                            # Add entity attributes if configured
                            self._add_entity_attributes(entity, instance_uri, entity_type)

                            # Add inverse attributes if configured
                            self._add_inverse_attributes(entity, instance_uri, entity_type)
                            
                            processed_count += 1
                    
                    except Exception as e:
                        logger.debug(f"Error processing entity {entity.id()}: {e}")
                        continue
            
            # Process spatial relationships
            self._process_spatial_relationships()
            
            logger.info(f"RDF entities created: {processed_count}")
            
        except Exception as e:
            error_msg = f"Error creating RDF entities: {e}"
            logger.error(error_msg)
            self.conversion_results['errors'].append(error_msg)
    
    def _add_cached_properties(self, entity, instance_uri: URIRef, global_id: str):
        """Add cached properties and quantities to entity"""
        try:
            # Get original GlobalId from entity for property lookup
            original_global_id = getattr(entity, 'GlobalId', global_id)
            
            if original_global_id in self.properties_cache:
                cached_props = self.properties_cache[original_global_id]
                
                # Add property sets
                for pset in cached_props.get('psets', []):
                    pset_name = pset.get('name', '')
                    if pset_name in self.conversion_map.get('psets', {}):
                        for key, value_uri in self.conversion_map['psets'][pset_name].items():
                            if key in pset and pset[key] is not None:
                                self.graph.add((instance_uri, URIRef(value_uri), Literal(pset[key])))
                
                # Add quantity sets
                for qset in cached_props.get('qsets', []):
                    qset_name = qset.get('name', '')
                    if qset_name in self.conversion_map.get('qsets', {}):
                        for key, value_uri in self.conversion_map['qsets'][qset_name].items():
                            if key in qset and qset[key] is not None:
                                self.graph.add((instance_uri, URIRef(value_uri), Literal(qset[key])))
        
        except Exception as e:
            logger.debug(f"Error adding cached properties for entity: {e}")
    
    def _add_entity_attributes(self, entity, instance_uri: URIRef, entity_type: str):
        """Add entity attributes based on conversion map"""
        try:
            attrs_config = self.conversion_map['classes'][entity_type].get('attrs', {})
            
            if not attrs_config:
                return
            
            entity_schema = self.schema.declaration_by_name(entity_type)
            attr_count = entity_schema.attribute_count()
            
            for i in range(attr_count):
                try:
                    attr = entity_schema.attribute_by_index(i)
                    attr_name = attr.name()
                    
                    if attr_name not in attrs_config:
                        continue
                    
                    # Get attribute value safely
                    try:
                        attr_value = entity[i]
                    except RuntimeError:
                        if not attr.optional():
                            logger.debug(f"Required attribute {attr_name} missing for entity {entity.id()}")
                        continue
                    
                    if attr_value is None:
                        continue
                    
                    property_uri = URIRef(attrs_config[attr_name])
                    
                    # Add simple attribute values
                    if isinstance(attr_value, (str, int, float, bool)):
                        # Determine XSD type
                        if isinstance(attr_value, str):
                            datatype = self.namespaces['XSD'].string
                        elif isinstance(attr_value, bool):
                            datatype = self.namespaces['XSD'].boolean
                        elif isinstance(attr_value, int):
                            datatype = self.namespaces['XSD'].integer
                        elif isinstance(attr_value, float):
                            datatype = self.namespaces['XSD'].float
                        else:
                            datatype = self.namespaces['XSD'].string
                        
                        self.graph.add((instance_uri, property_uri, Literal(attr_value, datatype=datatype)))
                    
                    # Handle entity references
                    elif hasattr(attr_value, 'is_a') and attr_value.is_a() in self.conversion_map['classes']:
                        referenced_uri, _ = self._get_instance_uri(attr_value)
                        self.graph.add((instance_uri, property_uri, referenced_uri))
                
                except Exception as e:
                    logger.debug(f"Error processing attribute {attr_name}: {e}")
                    continue
        
        except Exception as e:
            logger.debug(f"Error adding entity attributes: {e}")
    
    def _add_inverse_attributes(self, entity, instance_uri: URIRef, entity_type: str):
        """Add inverse attributes based on conversion map"""
        try:
            inv_attrs_config = self.conversion_map['classes'][entity_type].get('inv_attrs', {})
            
            if not inv_attrs_config:
                return
            
            entity_schema = self.schema.declaration_by_name(entity_type)
            inverse_attributes = entity_schema.all_inverse_attributes()
            
            for inv_attr in inverse_attributes:
                try:
                    inverse_attr_label = inv_attr.name()
                    
                    if inverse_attr_label not in inv_attrs_config:
                        continue
                    
                    inv_attr_uri = URIRef(inv_attrs_config[inverse_attr_label])
                    reference_entity = inv_attr.entity_reference()
                    
                    # Get reference entity attributes (excluding common ones)
                    reference_entity_attrs = [
                        item for item in reference_entity.all_attributes() 
                        if item.name() not in {
                            'GlobalId', 'OwnerHistory', 'Name', 'Description', 
                            'RelatedObjectsType', 'ActingRole', 'ConnectionGeometry',
                            'QuantityInProcess', 'SequenceType', 'TimeLag', 
                            'UserDefinedSequenceType'
                        }
                    ]
                    
                    # Skip if too many attributes (complex relationships)
                    if len(reference_entity_attrs) > 2:
                        continue
                    
                    # Determine the reference attribute
                    inverse_of_attr = inv_attr.attribute_reference()
                    reference_entity_attr = None
                    
                    if len(reference_entity_attrs) == 2:
                        # Find the attribute that's not the inverse
                        for ref_attr in reference_entity_attrs:
                            if inverse_of_attr.name() != ref_attr.name():
                                reference_entity_attr = ref_attr
                                break
                    elif len(reference_entity_attrs) == 1:
                        reference_entity_attr = reference_entity_attrs[0]
                    
                    if not reference_entity_attr:
                        continue
                    
                    # Get the relations from the entity
                    relations = getattr(entity, inv_attr.name(), None)
                    
                    if relations:
                        for relation in relations:
                            try:
                                content = getattr(relation, reference_entity_attr.name(), None)
                                
                                if content:
                                    self._add_inverse_relation_content(instance_uri, inv_attr_uri, content)
                            
                            except Exception as e:
                                logger.debug(f"Error processing relation: {e}")
                                continue
                
                except Exception as e:
                    logger.debug(f"Error processing inverse attribute {inverse_attr_label}: {e}")
                    continue
        
        except Exception as e:
            logger.debug(f"Error adding inverse attributes: {e}")
    
    def _add_inverse_relation_content(self, instance_uri: URIRef, inv_attr_uri: URIRef, content):
        """Add inverse relation content to graph"""
        try:
            if isinstance(content, (tuple, list)):
                # Handle collections
                for item in content:
                    if hasattr(item, 'is_a') and item.is_a() in self.conversion_map['classes']:
                        property_item_uri, _ = self._get_instance_uri(item)
                        self.graph.add((instance_uri, inv_attr_uri, property_item_uri))
            else:
                # Handle single items
                if hasattr(content, 'is_a') and content.is_a() in self.conversion_map['classes']:
                    property_item_uri, _ = self._get_instance_uri(content)
                    self.graph.add((instance_uri, inv_attr_uri, property_item_uri))
        
        except Exception as e:
            logger.debug(f"Error adding inverse relation content: {e}")

    def _process_spatial_relationships(self):
        """Process spatial aggregation relationships"""
        try:
            aggregations = self.ifc_file.by_type('IfcRelAggregates')
            
            for agg in aggregations:
                try:
                    relating_object = agg.RelatingObject
                    relating_uri, _ = self._get_instance_uri(relating_object)
                    
                    for related_object in agg.RelatedObjects:
                        related_uri, _ = self._get_instance_uri(related_object)
                        
                        # Only process spatial elements
                        if not relating_object.is_a('IfcSpatialElement'):
                            continue
                        
                        # Determine relationship type
                        if related_object.is_a('IfcSpace'):
                            relation = self.namespaces['BOT'].hasSpace
                        elif related_object.is_a('IfcBuildingStorey'):
                            relation = self.namespaces['BOT'].hasStorey
                        elif related_object.is_a('IfcBuilding') or related_object.is_a('IfcFacility'):
                            relation = self.namespaces['BOT'].hasBuilding
                        else:
                            logger.info(related_object)
                            relation = self.namespaces['BOT'].containsZone
                        
                        self.graph.add((relating_uri, relation, related_uri))
                
                except Exception as e:
                    logger.debug(f"Error processing aggregation: {e}")
                    continue
        
        except Exception as e:
            logger.debug(f"Error processing spatial relationships: {e}")
    
    def create_geometry_links(self, glb_file_path: Optional[str]):
        """Create RDF-geometry links using ontologies"""
        if not glb_file_path:
            return
        
        logger.info("Creating geometry links in RDF...")
        
        try:
            # Main geometry instance
            main_geometry_uri = self.namespaces['INST'][f"geometry_{self.asset_name}"]
            
            self.graph.add((main_geometry_uri, self.namespaces['RDF'].type, self.namespaces['OMG'].Geometry))
            self.graph.add((main_geometry_uri, self.namespaces['RDF'].type, self.namespaces['GOM'].MeshGeometry))
            self.graph.add((main_geometry_uri, self.namespaces['FOG']['asGltf_v2.0-glb'], 
                          Literal(glb_file_path, datatype=self.namespaces['XSD'].anyURI)))
            
            # Add metadata
            if os.path.exists(glb_file_path):
                file_size = os.path.getsize(glb_file_path)
                self.graph.add((main_geometry_uri, self.namespaces['GOM'].hasFileSize, 
                              Literal(file_size, datatype=self.namespaces['XSD'].nonNegativeInteger)))
            
            total_vertices = sum(elem['vertex_count'] for elem in self.elements_data)
            total_faces = sum(elem['face_count'] for elem in self.elements_data)
            
            self.graph.add((main_geometry_uri, self.namespaces['GOM'].hasVertices, 
                          Literal(total_vertices, datatype=self.namespaces['XSD'].nonNegativeInteger)))
            self.graph.add((main_geometry_uri, self.namespaces['GOM'].hasFaces, 
                          Literal(total_faces, datatype=self.namespaces['XSD'].nonNegativeInteger)))
            
            # Link individual elements
            for element_data in self.elements_data:
                try:
                    entity_uri = self.namespaces['INST'][element_data['global_id']]
                    element_geometry_uri = self.namespaces['INST'][f"geometry_{element_data['global_id']}_{element_data['representation_index']}"]
                    
                    # Link entity to geometry
                    self.graph.add((entity_uri, self.namespaces['OMG'].hasGeometry, element_geometry_uri))
                    
                    # Geometry metadata
                    self.graph.add((element_geometry_uri, self.namespaces['RDF'].type, self.namespaces['OMG'].Geometry))
                    self.graph.add((element_geometry_uri, self.namespaces['RDF'].type, self.namespaces['GOM'].MeshGeometry))
                    self.graph.add((element_geometry_uri, self.namespaces['OMG'].isPartOfGeometry, main_geometry_uri))
                    self.graph.add((element_geometry_uri, self.namespaces['GOM'].hasVertices, 
                                  Literal(element_data['vertex_count'], datatype=self.namespaces['XSD'].nonNegativeInteger)))
                    self.graph.add((element_geometry_uri, self.namespaces['GOM'].hasFaces, 
                                  Literal(element_data['face_count'], datatype=self.namespaces['XSD'].nonNegativeInteger)))
                
                except Exception as e:
                    logger.debug(f"Error linking geometry for element: {e}")
                    continue
            
            logger.info(f"Geometry links created for {len(self.elements_data)} elements")
            
        except Exception as e:
            logger.warning(f"Error creating geometry links: {e}")
    
    def save_rdf(self) -> Optional[str]:
        """Save RDF graph"""
        try:
            os.makedirs(self.rdf_output_path, exist_ok=True)
            rdf_file_path = os.path.join(self.rdf_output_path, f"{self.asset_name}.ttl")
            
            self.graph.serialize(destination=rdf_file_path, format='turtle')
            
            logger.info(f"RDF saved: {rdf_file_path} ({len(self.graph)} triples)")
            return rdf_file_path
            
        except Exception as e:
            error_msg = f"Error saving RDF: {e}"
            logger.error(error_msg)
            self.conversion_results['errors'].append(error_msg)
            return None
    
    def convert(self) -> Dict[str, Any]:
        """Main conversion method"""
        logger.info(f"Starting integrated conversion for: {self.asset_name}")
        
        try:
            # Load IFC
            if not self.load_ifc():
                self.conversion_results['success'] = False
                return self.conversion_results
            
            # Cache properties
            self._cache_properties()
            
            # Process geometry
            geometry_success = self.process_geometry()
            
            # Create GLB
            glb_file_path = None
            if geometry_success:
                glb_file_path = self.create_glb()
            
            # Create RDF entities
            self.create_rdf_entities()
            
            # Link geometry in RDF
            self.create_geometry_links(glb_file_path)
            
            # Save RDF
            rdf_file_path = self.save_rdf()
            
            # Prepare results
            self.conversion_results['success'] = True
            
            if rdf_file_path:
                self.conversion_results['files']['rdf'] = {
                    'path': rdf_file_path,
                    'size': os.path.getsize(rdf_file_path),
                    'format': 'turtle',
                    'triples': len(self.graph)
                }
            
            if glb_file_path:
                self.conversion_results['files']['glb'] = {
                    'path': glb_file_path,
                    'size': os.path.getsize(glb_file_path),
                    'format': 'glb',
                    'elements': len(self.elements_data)
                }
            
            self.conversion_results['metadata'] = {
                'asset_name': self.asset_name,
                'ifc_schema': str(self.ifc_file.schema),
                'entities_processed': len(self.created_entities),
                'geometry_elements': len(self.elements_data),
                'total_vertices': sum(elem['vertex_count'] for elem in self.elements_data) if self.elements_data else 0,
                'total_faces': sum(elem['face_count'] for elem in self.elements_data) if self.elements_data else 0
            }
            
            logger.info(f"Conversion completed successfully for: {self.asset_name}")
            
        except Exception as e:
            error_msg = f"Fatal error during conversion: {e}"
            logger.error(error_msg)
            self.conversion_results['errors'].append(error_msg)
            self.conversion_results['success'] = False
        
        return self.conversion_results


# Simple usage function for backward compatibility
def convert_ifc_file(ifc_file_path: str, 
                    asset_name: Optional[str] = None,
                    base_url: str = "http://localhost:8000/data/",
                    rdf_output_path: str = "./data/rdf",
                    glb_output_path: str = "./data/glb",
                    convert_geometry: bool = True,
                    conversion_map_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Simple function to convert IFC file
    
    Args:
        ifc_file_path: Path to IFC file
        asset_name: Name for output files
        base_url: Base URL for RDF namespaces
        rdf_output_path: Directory for RDF output
        glb_output_path: Directory for GLB output
        convert_geometry: Whether to generate GLB file
        conversion_map_path: Path to conversion-map.json file
    
    Returns:
        Dictionary with conversion results
    """
    
    converter = CompactIFCConverter(
        ifc_file_path=ifc_file_path,
        asset_name=asset_name,
        base_url=base_url,
        rdf_output_path=rdf_output_path,
        glb_output_path=glb_output_path,
        convert_geometry=convert_geometry,
        conversion_map_path=conversion_map_path
    )
    
    return converter.convert()


# Command line interface
def main():
    """Command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Compact IFC to RDF + GLB Converter')
    parser.add_argument('ifc_file', help='Path to IFC file')
    parser.add_argument('--asset-name', '-n', help='Asset name (default: filename)')
    parser.add_argument('--base-url', '-u', default='http://localhost:8000/data/', 
                       help='Base URL for RDF namespaces')
    parser.add_argument('--rdf-output', '-r', default='./data/rdf', 
                       help='RDF output directory')
    parser.add_argument('--glb-output', '-g', default='./data/glb',
                       help='GLB output directory')
    parser.add_argument('--no-geometry', action='store_true',
                       help='Skip GLB geometry conversion')
    parser.add_argument('--conversion-map', '-m', 
                       help='Path to custom conversion map JSON file')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load custom conversion map if provided
    conversion_map_path = None
    if args.conversion_map:
        try:
            with open(args.conversion_map, 'r', encoding='utf-8') as f:
                conversion_map_path = args.conversion_map
            logger.info(f"Using custom conversion map: {args.conversion_map}")
        except Exception as e:
            logger.warning(f"Could not load conversion map: {e}")
            conversion_map_path = None
    
    # Run conversion
    logger.info("=" * 60)
    logger.info("COMPACT IFC CONVERTER")
    logger.info("=" * 60)
    
    try:
        results = convert_ifc_file(
            ifc_file_path=args.ifc_file,
            asset_name=args.asset_name,
            base_url=args.base_url,
            rdf_output_path=args.rdf_output,
            glb_output_path=args.glb_output,
            convert_geometry=not args.no_geometry,
            conversion_map_path=conversion_map_path
        )
        
        if results['success']:
            logger.info("=" * 60)
            logger.info("CONVERSION COMPLETED SUCCESSFULLY!")
            logger.info("=" * 60)
            
            # Print file information
            for file_type, file_info in results['files'].items():
                logger.info(f"{file_type.upper()}: {file_info['path']} ({file_info['size']} bytes)")
            
            # Print metadata
            metadata = results['metadata']
            logger.info(f"Entities processed: {metadata['entities_processed']}")
            if metadata['geometry_elements'] > 0:
                logger.info(f"Geometry elements: {metadata['geometry_elements']}")
                logger.info(f"Total vertices: {metadata['total_vertices']}")
                logger.info(f"Total faces: {metadata['total_faces']}")
            
        else:
            logger.error("=" * 60)
            logger.error("CONVERSION FAILED!")
            logger.error("=" * 60)
            for error in results['errors']:
                logger.error(f"Error: {error}")
        
        return results['success']
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return False


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)