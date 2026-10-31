import pulumi
import pulumi_kubernetes as k8s

# 1. Dedicated System Namespace
system_ns = k8s.core.v1.Namespace(
    "platform-system-ns",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="platform-system",
        labels={
            "app.kubernetes.io/part-of": "enterprise-platform",
            "tier": "system-infrastructure",
        },
    ),
)

# 2. Database Credentials Secret
db_secret = k8s.core.v1.Secret(
    "postgres-credentials",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="postgres-credentials",
        namespace=system_ns.metadata.name,
    ),
    string_data={
        "POSTGRES_DB": "platform_db",
        "POSTGRES_USER": "platform_admin",
        "POSTGRES_PASSWORD": "EnterpriseSecurePassword2026!",
    },
)

# 3. Persistent Volume Claim for Database Durability
db_pvc = k8s.core.v1.PersistentVolumeClaim(
    "postgres-pvc",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="postgres-pvc",
        namespace=system_ns.metadata.name,
    ),
    spec=k8s.core.v1.PersistentVolumeClaimSpecArgs(
        access_modes=["ReadWriteOnce"],
        resources=k8s.core.v1.VolumeResourceRequirementsArgs(
            requests={"storage": "2Gi"}
        ),
    ),
)

# 4. PostgreSQL 16 Deployment with Resource Governance
db_deployment = k8s.apps.v1.Deployment(
    "postgres-deployment",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="postgres-deployment",
        namespace=system_ns.metadata.name,
        labels={"app": "platform-postgres", "tier": "database"},
    ),
    spec=k8s.apps.v1.DeploymentSpecArgs(
        replicas=1,
        selector=k8s.meta.v1.LabelSelectorArgs(
            match_labels={"app": "platform-postgres"}
        ),
        template=k8s.core.v1.PodTemplateSpecArgs(
            metadata=k8s.meta.v1.ObjectMetaArgs(
                labels={"app": "platform-postgres", "tier": "database"}
            ),
            spec=k8s.core.v1.PodSpecArgs(
                containers=[
                    k8s.core.v1.ContainerArgs(
                        name="postgres",
                        image="postgres:16-alpine",
                        env_from=[
                            k8s.core.v1.EnvFromSourceArgs(
                                secret_ref=k8s.core.v1.SecretEnvSourceArgs(
                                    name=db_secret.metadata.name
                                )
                            )
                        ],
                        ports=[
                            k8s.core.v1.ContainerPortArgs(
                                container_port=5432, name="postgres"
                            )
                        ],
                        resources=k8s.core.v1.ResourceRequirementsArgs(
                            requests={"cpu": "100m", "memory": "128Mi"},
                            limits={"cpu": "500m", "memory": "512Mi"},
                        ),
                        readiness_probe=k8s.core.v1.ProbeArgs(
                            exec_=k8s.core.v1.ExecActionArgs(
                                command=["pg_isready", "-U", "platform_admin", "-d", "platform_db"]
                            ),
                            initial_delay_seconds=5,
                            period_seconds=5,
                        ),
                        liveness_probe=k8s.core.v1.ProbeArgs(
                            exec_=k8s.core.v1.ExecActionArgs(
                                command=["pg_isready", "-U", "platform_admin", "-d", "platform_db"]
                            ),
                            initial_delay_seconds=15,
                            period_seconds=10,
                        ),
                        volume_mounts=[
                            k8s.core.v1.VolumeMountArgs(
                                mount_path="/var/lib/postgresql/data",
                                name="postgres-storage",
                            )
                        ],
                    )
                ],
                volumes=[
                    k8s.core.v1.VolumeArgs(
                        name="postgres-storage",
                        persistent_volume_claim=k8s.core.v1.PersistentVolumeClaimVolumeSourceArgs(
                            claim_name=db_pvc.metadata.name
                        ),
                    )
                ],
            ),
        ),
    ),
)

# 5. ClusterIP Service for Internal Routing
db_service = k8s.core.v1.Service(
    "postgres-service",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="postgres-service",
        namespace=system_ns.metadata.name,
        labels={"app": "platform-postgres"},
    ),
    spec=k8s.core.v1.ServiceSpecArgs(
        type="ClusterIP",
        ports=[
            k8s.core.v1.ServicePortArgs(
                port=5432, target_port=5432, name="postgres"
            )
        ],
        selector={"app": "platform-postgres"},
    ),
)

# 6. Export connection outputs
pulumi.export("system_namespace", system_ns.metadata.name)
pulumi.export("postgres_service_name", db_service.metadata.name)
pulumi.export(
    "postgres_internal_fqdn",
    pulumi.Output.concat(
        db_service.metadata.name, ".", system_ns.metadata.name, ".svc.cluster.local"
    ),
)
