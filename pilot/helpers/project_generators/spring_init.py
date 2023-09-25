import os
import subprocess
from helpers.Project import Project
from .project_generator import project_generator


@project_generator(name="spring init",
                   language="Java, Kotlin",
                   topics=["Spring", "Java", "Kotlin"])
class SpringInit:
    """
    Creates a new Spring Boot app using Spring Initializr
    See https://docs.spring.io/spring-boot/docs/current/reference/html/cli.html
    """

    def create_new_project(self, project: Project):
        cmd = ['spring', 'init',
               '--name', project.name,
               '--artifact-id', project.name,
               # '--group', project.group,
               # '--package-name', project.package_name,
               '--build gradle',
               '--description', project.description,
                # '--java-version', project.java_version,
                # '--language', project.language,  # 'java', 'kotlin', 'groovy'
               ]

        # TODO: send output of `spring init -list` to LLM to select dependencies

        # activemq, actuator, amqp, artemis,
        # azure-active-directory, azure-cosmos-db, azure-keyvault, azure-storage, azure-support
        # batch, cache, camel, cloud-bus, cloud-cloudfoundry-discovery, cloud-config-client, cloud-config-server
        # cloud-contract-stub-runner, cloud-contract-verifier, cloud-eureka, cloud-feign, cloud-function, cloud-gateway,
        # cloud-gcp, cloud-gcp-pubsub, cloud-gcp-storage, cloud-loadbalancer, cloud-resilience4j,
        # cloud-starter, cloud-starter-consul-config, cloud-starter-consul-discovery, cloud-starter-vault-config,
        # cloud-starter-zookeeper-config, cloud-starter-zookeeper-discovery, cloud-stream, cloud-task,
        # codecentric-spring-boot-admin-client, codecentric-spring-boot-admin-server, configuration-processor,
        # data-cassandra, data-cassandra-reactive, data-couchbase, data-couchbase-reactive, data-elasticsearch,
        # data-jdbc, data-jpa, data-ldap, data-mongodb, data-mongodb-reactive, data-neo4j, data-r2dbc, data-redis,
        # data-rest, data-rest-explorer, datadog, db2, derby, devtools, distributed-tracing
        # docker-compose, dynatrace, flapdoodle, flyway, freemarker, graphite, graphql, groovy-templates, h2, hateoas,
        # hilla, hsql, influx, integration, jdbc, jersey, jooq, kafka, kafka-streams, liquibase, lombok, mail, mariadb,
        # modulith, mustache, mybatis, mysql, native, new-relic,
        # oauth2-authorization-server, oauth2-client, oauth2-resource-server, okta, oracle, picocli, postgresql,
        # prometheus, pulsar, quartz, restdocs, rsocket, scs-config-client, security, sentry, session, solace
        # spring-shell, sqlserver, testcontainers, thymeleaf, unboundid-ldap, vaadin, validation, wavefront, web,
        # webflux, websocket, zipkin

        # '--dependencies web,actuator',

        # cmd.append(project.root_path)

        # Run the command
        os.chdir(project.root_path)
        subprocess.run(cmd)
