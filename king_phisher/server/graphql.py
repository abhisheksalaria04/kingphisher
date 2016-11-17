#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/graphql.py
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are
#  met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following disclaimer
#    in the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of the project nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import datetime

import king_phisher.geoip as geoip
import king_phisher.ipaddress as ipaddress
import king_phisher.server.database.models as db_models
import king_phisher.version as version

import graphene
import graphene.types
import graphene_sqlalchemy

# graphene replacement types
class DateTime(graphene.types.Scalar):
	@staticmethod
	def serialize(dt):
		return dt

	@staticmethod
	def parse_literal(node):
		if isinstance(node, graphene.language.ast.StringValue):
			return datetime.datetime.strptime(node.value, '%Y-%m-%dT%H:%M:%S.%f')

	@staticmethod
	def parse_value(value):
		return datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f')

class RelayNode(graphene.relay.Node):
	@classmethod
	def from_global_id(cls, global_id):
		return global_id

	@classmethod
	def to_global_id(cls, type, local_id):
		return local_id

# misc objects
class GeoLocation(graphene.ObjectType):
	city = graphene.Field(graphene.String)
	continent = graphene.Field(graphene.String)
	coordinates = graphene.List(graphene.Float)
	country = graphene.Field(graphene.String)
	postal_code = graphene.Field(graphene.String)
	time_zone = graphene.Field(graphene.String)

	@classmethod
	def from_ip_address(cls, ip_address):
		ip_address = ipaddress.ip_address(ip_address)
		if ip_address.is_private:
			return
		result = geoip.lookup(ip_address)
		if result is None:
			return
		return cls(**result)

class Plugin(graphene.ObjectType):
	class Meta:
		interfaces = (RelayNode,)
	authors = graphene.List(graphene.String)
	title = graphene.Field(graphene.String)
	description = graphene.Field(graphene.String)
	homepage = graphene.Field(graphene.String)
	name = graphene.Field(graphene.String)
	version = graphene.Field(graphene.String)

	@classmethod
	def from_plugin(cls, plugin):
		return cls(
			authors=plugin.authors,
			description=plugin.description,
			homepage=plugin.homepage,
			name=plugin.name,
			title=plugin.title,
			version=plugin.version
		)

# database objects
class AlertSubscription(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.AlertSubscription
		interfaces = (RelayNode,)
	mute_timestamp = DateTime()

class Credential(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.Credential
		interfaces = (RelayNode,)
	submitted = DateTime()

class DeaddropConnection(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.DeaddropConnection
		interfaces = (RelayNode,)
	first_visit = DateTime()
	last_visit = DateTime()

class DeaddropDeployment(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.DeaddropDeployment
		interfaces = (RelayNode,)
	# relationships
	deaddrop_connections = graphene_sqlalchemy.SQLAlchemyConnectionField(DeaddropConnection)

class LandingPage(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.LandingPage
		interfaces = (RelayNode,)

class Visit(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.Visit
		interfaces = (RelayNode,)
	first_visit = DateTime()
	last_visit = DateTime()
	visitor_geoloc = graphene.Field(GeoLocation)
	# relationships
	credentials = graphene_sqlalchemy.SQLAlchemyConnectionField(Credential)

	def resolve_visitor_geoloc(self, args, context, info):
		visitor_ip = self.visitor_ip
		if not visitor_ip:
			return
		return GeoLocation.from_ip_address(visitor_ip)

class Message(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.Message
		interfaces = (RelayNode,)
	opened = DateTime()
	sent = DateTime()
	# relationships
	credentials = graphene_sqlalchemy.SQLAlchemyConnectionField(Credential)
	visits = graphene_sqlalchemy.SQLAlchemyConnectionField(Visit)

class Campaign(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.Campaign
		interfaces = (RelayNode,)
	created = DateTime()
	expiration = DateTime()
	# relationships
	alert_subscriptions = graphene_sqlalchemy.SQLAlchemyConnectionField(AlertSubscription)
	credentials = graphene_sqlalchemy.SQLAlchemyConnectionField(Credential)
	deaddrop_connections = graphene_sqlalchemy.SQLAlchemyConnectionField(DeaddropConnection)
	deaddrop_deployments = graphene_sqlalchemy.SQLAlchemyConnectionField(DeaddropDeployment)
	landing_pages = graphene_sqlalchemy.SQLAlchemyConnectionField(LandingPage)
	messages = graphene_sqlalchemy.SQLAlchemyConnectionField(Message)
	visits = graphene_sqlalchemy.SQLAlchemyConnectionField(Visit)

class CampaignType(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.CampaignType
		interfaces = (RelayNode,)
	# relationships
	campaigns = graphene_sqlalchemy.SQLAlchemyConnectionField(Campaign)

class Company(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.Company
		interfaces = (RelayNode,)
	# relationships
	campaigns = graphene_sqlalchemy.SQLAlchemyConnectionField(Campaign)

class CompanyDepartment(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.CompanyDepartment
		interfaces = (RelayNode,)
	# relationships
	messages = graphene_sqlalchemy.SQLAlchemyConnectionField(Message)

class Industry(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.Industry
		interfaces = (RelayNode,)
	# relationships
	companies = graphene_sqlalchemy.SQLAlchemyConnectionField(Company)

class User(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.User
		interfaces = (RelayNode,)
	# relationships
	alert_subscriptions = graphene_sqlalchemy.SQLAlchemyConnectionField(AlertSubscription)
	campaigns = graphene_sqlalchemy.SQLAlchemyConnectionField(Campaign)

class Database(graphene.ObjectType):
	alert_subscriptions = graphene_sqlalchemy.SQLAlchemyConnectionField(AlertSubscription)
	campaign_type = graphene.Field(CampaignType, id=graphene.Int())
	campaign_types = graphene_sqlalchemy.SQLAlchemyConnectionField(CampaignType)
	campaign = graphene.Field(Campaign, id=graphene.Int())
	campaigns = graphene_sqlalchemy.SQLAlchemyConnectionField(Campaign)
	company = graphene.Field(Company, id=graphene.Int())
	companies = graphene_sqlalchemy.SQLAlchemyConnectionField(Company)
	company_department = graphene.Field(CompanyDepartment, id=graphene.Int())
	company_departments = graphene_sqlalchemy.SQLAlchemyConnectionField(CompanyDepartment)
	credential = graphene.Field(Credential, id=graphene.Int())
	credentials = graphene_sqlalchemy.SQLAlchemyConnectionField(Credential)
	deaddrop_connection = graphene.Field(DeaddropConnection, id=graphene.Int())
	deaddrop_connections = graphene_sqlalchemy.SQLAlchemyConnectionField(DeaddropConnection)
	deaddrop_deployment = graphene.Field(DeaddropDeployment, id=graphene.String())
	deaddrop_deployments = graphene_sqlalchemy.SQLAlchemyConnectionField(DeaddropDeployment)
	industry = graphene.Field(Industry, id=graphene.Int())
	industries = graphene_sqlalchemy.SQLAlchemyConnectionField(Industry)
	landing_page = graphene.Field(LandingPage, id=graphene.Int())
	landing_pages = graphene_sqlalchemy.SQLAlchemyConnectionField(LandingPage)
	message = graphene.Field(Message, id=graphene.String())
	messages = graphene_sqlalchemy.SQLAlchemyConnectionField(Message)
	user = graphene.Field(User, id=graphene.String())
	users = graphene_sqlalchemy.SQLAlchemyConnectionField(User)
	visit = graphene.Field(Visit, id=graphene.String())
	visits = graphene_sqlalchemy.SQLAlchemyConnectionField(Visit)

	def resolve_alert_subscription(self, args, context, info):
		query = AlertSubscription.get_query(context)
		query = query.filter_by(**args)
		return query.first()

	def resolve_alert_subscriptions(self, args, context, info):
		query = AlertSubscription.get_query(context)
		return query.all()

	def resolve_campaign(self, args, context, info):
		query = Campaign.get_query(context)
		query = query.filter_by(**args)
		return query.first()

	def resolve_campaigns(self, args, context, info):
		query = Campaign.get_query(context)
		return query.all()

	def resolve_campaign_type(self, args, context, info):
		query = CampaignType.get_query(context)
		query = query.filter_by(**args)
		return query.first()

	def resolve_campaign_types(self, args, context, info):
		query = CampaignType.get_query(context)
		return query.all()

	def resolve_company(self, args, context, info):
		query = Company.get_query(context)
		query = query.filter_by(**args)
		return query.first()

	def resolve_companies(self, args, context, info):
		query = Company.get_query(context)
		return query.all()

	def resolve_company_department(self, args, context, info):
		query = CompanyDepartment.get_query(context)
		query = query.filter_by(**args)
		return query.first()

	def resolve_company_departments(self, args, context, info):
		query = CompanyDepartment.get_query(context)
		return query.all()

	def resolve_credential(self, args, context, info):
		query = Credential.get_query(context)
		query = query.filter_by(**args)
		return query.first()

	def resolve_credentials(self, args, context, info):
		query = Credential.get_query(context)
		return query.all()

	def resolve_deaddrop_connection(self, args, context, info):
		query = DeaddropConnection.get_query(context)
		query = query.filter_by(**args)
		return query.first()

	def resolve_deaddrop_connections(self, args, context, info):
		query = DeaddropConnection.get_query(context)
		return query.all()

	def resolve_deaddrop_deployment(self, args, context, info):
		query = DeaddropDeployment.get_query(context)
		query = query.filter_by(**args)
		return query.first()

	def resolve_deaddrop_deployments(self, args, context, info):
		query = DeaddropDeployment.get_query(context)
		return query.all()

	def resolve_industry(self, args, context, info):
		query = Industry.get_query(context)
		query = query.filter_by(**args)
		return query.first()

	def resolve_industries(self, args, context, info):
		query = Industry.get_query(context)
		return query.all()

	def resolve_landing_page(self, args, context, info):
		query = LandingPage.get_query(context)
		query = query.filter_by(**args)
		return query.first()

	def resolve_landing_pages(self, args, context, info):
		query = LandingPage.get_query(context)
		return query.all()

	def resolve_message(self, args, context, info):
		query = Message.get_query(context)
		query = query.filter_by(**args)
		return query.first()

	def resolve_messages(self, args, context, info):
		query = Message.get_query(context)
		return query.all()

	def resolve_user(self, args, context, info):
		query = User.get_query(context)
		query = query.filter_by(**args)
		return query.first()

	def resolve_users(self, args, context, info):
		query = User.get_query(context)
		return query.all()

	def resolve_visit(self, args, context, info):
		query = Visit.get_query(context)
		query = query.filter_by(**args)
		return query.first()

	def resolve_visits(self, args, context, info):
		query = Visit.get_query(context)
		return query.all()

class Query(graphene.ObjectType):
	db = graphene.Field(Database)
	geoloc = graphene.Field(GeoLocation, ip=graphene.String())
	plugin = graphene.Field(Plugin, name=graphene.String())
	plugins = graphene.relay.ConnectionField(Plugin)
	version = graphene.Field(graphene.String)

	def resolve_db(self, args, context, info):
		return Database()

	def resolve_geoloc(self, args, context, info):
		ip_address = args.get('ip')
		if ip_address is None:
			return
		return GeoLocation.from_ip_address(ip_address)

	def resolve_plugin(self, args, context, info):
		for _, plugin in context['plugin_manager']:
			if plugin.name != args.get('name'):
				continue
			return Plugin.from_plugin(plugin)

	def resolve_plugins(self, args, context, info):
		return [Plugin.from_plugin(plugin) for _, plugin in sorted(context['plugin_manager'], key=lambda i: i[0])]

	def resolve_version(self, args, context, info):
		return version.version

class AuthorizationMiddleware(object):
	def resolve(self, next, root, args, context, info):
		rpc_session = context.get('rpc_session')
		if isinstance(root, db_models.Base) and rpc_session is not None:
			if not root.session_has_read_prop_access(rpc_session, info.field_name):
				return
		return next(root, args, context, info)

class Schema(graphene.Schema):
	def __init__(self, **kwargs):
		kwargs['auto_camelcase'] = True
		kwargs['query'] = Query
		super(Schema, self).__init__(**kwargs)

	def execute(self, *args, **kwargs):
		middleware = list(kwargs.pop('middleware', []))
		middleware.insert(0, AuthorizationMiddleware())
		kwargs['middleware'] = middleware
		return super(Schema, self).execute(*args, **kwargs)

	def execute_file(self, path, *args, **kwargs):
		with open(path, 'r') as file_h:
			query = file_h.read()
		return self.execute(query, *args, **kwargs)

schema = Schema()
