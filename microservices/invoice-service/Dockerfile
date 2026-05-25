FROM eclipse-temurin:21-jre-alpine
VOLUME /tmp
COPY target/invoice-service-0.0.1-SNAPSHOT.jar app.jar
ENTRYPOINT ["java", \
  "-Xms256m", \
  "-Xmx512m", \
  "-XX:+UseG1GC", \
  "-Djava.security.egd=file:/dev/./urandom", \
  "-jar", "/app.jar"]
