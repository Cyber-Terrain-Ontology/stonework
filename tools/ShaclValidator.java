import java.io.File;
import java.io.InputStream;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import org.eclipse.rdf4j.model.IRI;
import org.eclipse.rdf4j.model.Model;
import org.eclipse.rdf4j.model.Resource;
import org.eclipse.rdf4j.model.Statement;
import org.eclipse.rdf4j.model.Value;
import org.eclipse.rdf4j.model.impl.LinkedHashModel;
import org.eclipse.rdf4j.model.impl.SimpleValueFactory;
import org.eclipse.rdf4j.model.vocabulary.RDF4J;
import org.eclipse.rdf4j.query.BindingSet;
import org.eclipse.rdf4j.query.QueryLanguage;
import org.eclipse.rdf4j.query.TupleQueryResult;
import org.eclipse.rdf4j.repository.RepositoryConnection;
import org.eclipse.rdf4j.repository.sail.SailRepository;
import org.eclipse.rdf4j.repository.sail.SailRepositoryConnection;
import org.eclipse.rdf4j.rio.RDFFormat;
import org.eclipse.rdf4j.rio.Rio;
import org.eclipse.rdf4j.sail.memory.MemoryStore;
import org.eclipse.rdf4j.sail.shacl.ShaclSail;
import org.eclipse.rdf4j.sail.shacl.ShaclSailConnection;
import org.eclipse.rdf4j.sail.shacl.results.ValidationReport;

public final class ShaclValidator {
    private static final String SHACL = "http://www.w3.org/ns/shacl#";
    private static final IRI SH_PATH = SimpleValueFactory.getInstance().createIRI(SHACL + "path");
    private static final IRI SH_LESS_THAN_OR_EQUALS =
        SimpleValueFactory.getInstance().createIRI(SHACL + "lessThanOrEquals");

    private static final class OrderingConstraint {
        private final IRI path;
        private final IRI upperBoundPath;

        private OrderingConstraint(IRI path, IRI upperBoundPath) {
            this.path = path;
            this.upperBoundPath = upperBoundPath;
        }
    }

    private ShaclValidator() {}

    private static RDFFormat formatFor(File file) {
        Optional<RDFFormat> format = Rio.getParserFormatForFileName(file.getName());
        return format.orElse(RDFFormat.TURTLE);
    }

    private static Model readShapes(File file) throws Exception {
        try (InputStream stream = Files.newInputStream(file.toPath())) {
            return Rio.parse(stream, file.toURI().toString(), formatFor(file));
        }
    }

    private static List<OrderingConstraint> orderingConstraints(Model shapes) {
        List<OrderingConstraint> constraints = new ArrayList<>();
        for (Statement statement : shapes.filter(null, SH_LESS_THAN_OR_EQUALS, null)) {
            Resource propertyShape = statement.getSubject();
            Value upperBound = statement.getObject();
            if (!(upperBound instanceof IRI)) {
                continue;
            }
            for (Value path : shapes.filter(propertyShape, SH_PATH, null).objects()) {
                if (path instanceof IRI) {
                    constraints.add(new OrderingConstraint((IRI) path, (IRI) upperBound));
                }
            }
        }
        return constraints;
    }

    private static List<String> validateOrdering(
        RepositoryConnection connection,
        List<OrderingConstraint> constraints
    ) {
        List<String> failures = new ArrayList<>();
        for (OrderingConstraint constraint : constraints) {
            String query = String.format(
                "SELECT ?focus ?left ?right WHERE { "
                    + "?focus <%s> ?left ; <%s> ?right . FILTER (?left > ?right) }",
                constraint.path.stringValue(),
                constraint.upperBoundPath.stringValue()
            );
            try (TupleQueryResult results = connection
                .prepareTupleQuery(QueryLanguage.SPARQL, query)
                .evaluate()) {
                while (results.hasNext()) {
                    BindingSet result = results.next();
                    failures.add(String.format(
                        "%s: %s value %s must be no later than %s value %s",
                        result.getValue("focus"),
                        constraint.path,
                        result.getValue("left"),
                        constraint.upperBoundPath,
                        result.getValue("right")
                    ));
                }
            }
        }
        return failures;
    }

    @SuppressWarnings("deprecation")
    public static void main(String[] args) throws Exception {
        if (args.length < 4) {
            System.err.println(
                "Usage: ShaclValidator SHAPES CORE_SCHEMA CATEGORY_SCHEMA DATA [DATA ...]"
            );
            System.exit(2);
        }

        ShaclSail shaclSail = new ShaclSail(new MemoryStore());
        shaclSail.setRdfsSubClassReasoning(true);
        shaclSail.disableValidation();

        SailRepository repository = new SailRepository(shaclSail);
        repository.init();

        try (RepositoryConnection connection = repository.getConnection()) {
            connection.begin();
            File shapes = new File(args[0]);
            Model shapeModel = readShapes(shapes);
            List<OrderingConstraint> ordering = orderingConstraints(shapeModel);
            Model engineShapes = new LinkedHashModel(shapeModel);
            engineShapes.remove(null, SH_LESS_THAN_OR_EQUALS, null);
            connection.add(engineShapes, RDF4J.SHACL_SHAPE_GRAPH);
            connection.commit();

            connection.begin();
            for (int index = 1; index <= 2; index++) {
                File schema = new File(args[index]);
                connection.add(schema, formatFor(schema));
            }
            connection.commit();

            connection.begin();
            for (int index = 3; index < args.length; index++) {
                File data = new File(args[index]);
                connection.add(data, formatFor(data));
            }
            connection.commit();

            shaclSail.enableValidation();
            SailRepositoryConnection sailConnection = (SailRepositoryConnection) connection;
            ShaclSailConnection shaclConnection =
                (ShaclSailConnection) sailConnection.getSailConnection();
            connection.begin();
            ValidationReport validation = shaclConnection.revalidate();
            Model report = validation.asModel();
            connection.rollback();
            List<String> orderingFailures = validateOrdering(connection, ordering);
            if (!validation.conforms() || !orderingFailures.isEmpty()) {
                System.err.println("SHACL validation failed:");
                if (!validation.conforms()) {
                    Rio.write(report, System.err, RDFFormat.TURTLE);
                }
                for (String failure : orderingFailures) {
                    System.err.println("  - " + failure);
                }
                System.exit(1);
            }
        } finally {
            repository.shutDown();
        }

        System.out.printf("SHACL validation passed (%d data file(s)).%n", args.length - 3);
    }
}
