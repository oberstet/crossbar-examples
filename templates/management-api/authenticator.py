###############################################################################
##
##  Copyright (C) Tavendo GmbH and/or collaborators. All rights reserved.
##
##  Redistribution and use in source and binary forms, with or without
##  modification, are permitted provided that the following conditions are met:
##
##  1. Redistributions of source code must retain the above copyright notice,
##     this list of conditions and the following disclaimer.
##
##  2. Redistributions in binary form must reproduce the above copyright notice,
##     this list of conditions and the following disclaimer in the documentation
##     and/or other materials provided with the distribution.
##
##  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
##  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
##  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
##  ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
##  LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
##  CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
##  SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
##  INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
##  CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
##  ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
##  POSSIBILITY OF SUCH DAMAGE.
##
###############################################################################

import os
from pprint import pprint


from twisted.internet.defer import inlineCallbacks, returnValue

from autobahn.twisted.wamp import ApplicationSession
from autobahn.wamp.exception import ApplicationError

from autobahn.twisted.util import sleep


class AuthenticatorSession(ApplicationSession):

   @inlineCallbacks
   def onJoin(self, details):

      @inlineCallbacks
      def authenticate(realm, authid, details):
         print("WAMP-Anonymous dynamic authenticator invoked: realm='{}', authid='{}'".format(realm, authid))

         realm = realm or 'default'
         controller = self.config.controller
         worker = details['worker']
         realm_id = 'realm-{}'.format(realm)
         role = 'public'

         # crossbar.node.corei7ub1310.worker.worker-001.is_router_realm_running
         is_running = yield controller.call('{}.is_router_realm_running'.format(worker), realm_id)

         if is_running:
            self.log.info("Realm {realm} ALREADY RUNNING", realm=realm)
         else:
            self.log.info("Realm {realm} NOT RUNNING .. starting", realm=realm)

            realm_config = {
               "name": realm,
               "roles": [
                  {
                     "name": "public",
                     "permissions": [
                        {
                           "uri": "",
                           "match": "prefix",
                           "allow": {
                              "call": True,
                              "register": True,
                              "publish": True,
                              "subscribe": True
                           },
                           "cache": True
                        }
                     ]
                  }
               ]
            }

            # crossbar.node.corei7ub1310.worker.worker-001.start_router_realm
            try:
               yield self.config.controller.call('{}.start_router_realm'.format(worker), realm_id, realm_config)
            except Exception as e:
               self.log.error("REALM CREATION FAILED")
               self.log.error(e)
            else:
               self.log.info("REALM CREATED")

            role_id = 'role-{}-{}'.format(realm, role)
            role_config = {
               "name": role,
               "permissions": [
                  {
                     "uri": "",
                     "match": "prefix",
                     "allow": {
                        "call": True,
                        "register": True,
                        "publish": True,
                        "subscribe": True
                     },
                     "cache": True
                  }
               ]
            }

            # crossbar.node.corei7ub1310.worker.worker-001.start_router_realm_role
            try:
               yield self.config.controller.call('{}.start_router_realm_role'.format(worker), realm_id, role_id, role_config)
            except Exception as e:
               self.log.error("ROLE CREATION FAILED")
               self.log.error(e)
            else:
               self.log.info("ROLE CREATED")


            container_id = 'backend-{}'.format(realm)
            container_options = {
               "pythonpath": [".."]
            }

            node_id = 'thinkpad-t430s'
            try:
               yield self.config.controller.call('crossbar.node.{}.start_container'.format(node_id), container_id, container_options)
            except Exception as e:
               self.log.error("CONTAINER CREATION FAILED")
               self.log.error(e)
            else:
               self.log.info("CONTAINER CREATED")

            component_id = 'backend-{}'.format(realm)
            component_config = {
               "type": "class",
               "classname": "backend.Backend",
               "realm": realm,
               "transport": {
                  "type": "websocket",
                  "endpoint": {
                     "type": "tcp",
                     "host": "localhost",
                     "port": 8080
                  },
                  "url": "ws://localhost:8080/ws"
               }
            }

            # crossbar.node.corei7ub1310.worker.backend-realm1.start_container_component
            try:
               yield self.config.controller.call('crossbar.node.{}.worker.{}.start_container_component'.format(node_id, container_id), component_id, component_config)
            except Exception as e:
               self.log.error("COMPONENT CREATION FAILED")
               self.log.error(e)
            else:
               self.log.info("COMPONENT CREATED")


         principal = {
            'realm': realm,
            'role': role,
            'extra': {
               'eins': 'zwo',
               'drei': [4, 5, 6]
            }
         }

         self.log.info("Authenticator finished")

         returnValue(principal)

      try:
         yield self.register(authenticate, 'com.example.authenticate')
         print("WAMP-Anonymous dynamic authenticator registered!")
      except Exception as e:
         print("Failed to register dynamic authenticator: {0}".format(e))
