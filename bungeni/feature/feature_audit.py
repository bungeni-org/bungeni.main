# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Audit feature implementation

$Id$
"""
log = __import__("logging").getLogger("bungeni.feature.audit")


import sqlalchemy as sa
from sqlalchemy.orm import mapper, class_mapper, relation
from bungeni.alchemist.catalyst import MODEL_MODULE
from bungeni.alchemist.model import mapper_add_relation_vertical_property
from bungeni.alchemist import utils
from bungeni.models import domain, schema, interfaces as model_ifaces
from bungeni.utils import naming
from bungeni.capi import capi

from bungeni.feature import feature
from bungeni.feature import interfaces



class Audit(feature.Feature):
    """Support for the "audit" feature.
    """
    # parameter defaults
    AUDIT_ACTIONS = " ".join(domain.AUDIT_ACTIONS) # "add modify workflow remove version translate"
    INCLUDE_SUBTYPES = "attachment event signatory group_assignment member"
    DISPLAY_COLUMNS = "user date_active object description note date_audit"
    
    feature_interface = interfaces.IFeatureAudit
    feature_parameters = {
        "audit_actions": dict(type="sst", default=AUDIT_ACTIONS),
        "include_subtypes": dict(type="sst", default=INCLUDE_SUBTYPES),
        "display_columns": dict(type="sst", default=DISPLAY_COLUMNS),
    }
    subordinate_interface = model_ifaces.IChange # !+IAudit?
    
    def decorate_model(self, model):
        # Assumption: if a domain class is explicitly pre-defined, then it is 
        # assumed that all necessary setup is also taken care of. 
        # Typically, only the sub-classes of an archetype (mapped to a same 
        # table) need dynamic creation/setup.
        
        def get_audit_class_for(auditable_class):
            audit_cls_name = "%sAudit" % (auditable_class.__name__)
            return getattr(MODEL_MODULE, audit_cls_name, None)
        
        def get_base_audit_class(model):
            """Identify what should be the BASE audit class for a 
            {model}Audit class to inherit from, and return it.
            """
            assert interfaces.IFeatureAudit.implementedBy(model), model
            ti = capi.get_type_info(model)
            if ti.archetype is None:
                # !+ should this be allowed to ever happen? 
                # i.e. require each type to declare an archetype?
                base_audit_class = domain.Audit
            else:
                base_audit_class = get_audit_class_for(ti.archetype)
                if base_audit_class is None:
                    # fallback to get the audit class for the sys archetype
                    base_audit_class = get_audit_class_for(ti.sys_archetype)
                assert base_audit_class is not None, (model, ti.archetype, base_audit_class)
            return base_audit_class
        
        def new_audit_class(model):
            """Create, set on MODEL_MODULE, and map {model}Audit class.
            """
            base_audit_cls = get_base_audit_class(model)
            audit_cls = base_audit_cls.auditFactory(model)
            # set on MODEL_MODULE
            setattr(MODEL_MODULE, audit_cls.__name__, audit_cls)
            # mapper for newly created audit_cls
            mapper(audit_cls,
                inherits=base_audit_cls,
                polymorphic_identity=naming.polymorphic_identity(model)
            )
            log.info("GENERATED new_audit_class %s(%s) for type %s",
                audit_cls, base_audit_cls, model)
            return audit_cls
        
        # domain - audit class
        audit_cls = get_audit_class_for(model)
        if audit_cls is None: 
            audit_cls = new_audit_class(model)
        
        # auditor - head cls
        import bungeni.core.audit
        bungeni.core.audit.set_auditor(model)
        
        # mapper - audit class
        # assumption: audit_cls uses single inheritance only (and not only for 
        # those created dynamically in feature_audit())
        base_audit_cls = audit_cls.__bases__[0]
        assert issubclass(base_audit_cls, domain.Audit), \
            "Audit class %s is not a proper subclass of %s" % (
                audit_cls, domain.Audit)
        
        # extended attributes - propagate any on head cls also to its audit_cls
        for vp_name, vp_type in model.extended_properties:
            mapper_add_relation_vertical_property(
                audit_cls, vp_name, vp_type)
        # !+NOTE: capi.get_type_info(model).descriptor_model is still None

        # model.changes <-> change.audit.audit_head=doc:
        # doc[@TYPE] <-- TYPE_audit <-> audit <-> change
                
        # get head table for kls, and its audit table.
        tbl = utils.get_local_table(model)
        # NOT mapped_table, as when cls_mapper.single=False (e.g. for 
        # the case of the group type) it gves an sa.sql.expression.Join,
        # and not a table object:
        #   principal JOIN "group" ON principal.principal_id = "group".group_id
        audit_tbl = getattr(schema, naming.audit_table_name(tbl.name))
        cls_mapper = class_mapper(model)
        cls_mapper.add_property("changes", relation(domain.Change,
                # join condition, may be determined by a composite primary key
                primaryjoin=sa.and_( *[
                    pk_col == audit_tbl.c.get(pk_col.name)
                    for pk_col in tbl.primary_key ]),
                secondary=audit_tbl,
                secondaryjoin=sa.and_(
                    audit_tbl.c.audit_id == schema.change.c.audit_id,
                ),
                lazy=True,
                order_by=schema.change.c.audit_id.desc(),
                cascade="all",
                passive_deletes=False, # SA default
            ))
    
    # feature class utilities
    
    # contextual


