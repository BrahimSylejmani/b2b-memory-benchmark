package com.b2b.invoice.service;

import com.b2b.invoice.client.OrderClient;
import com.b2b.invoice.client.PartnerClient;
import com.b2b.invoice.entity.Invoice;
import com.b2b.invoice.repository.InvoiceRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Service
@Transactional
public class InvoiceService {

    private final InvoiceRepository repo;
    private final PartnerClient partnerClient;
    private final OrderClient orderClient;

    public InvoiceService(InvoiceRepository repo, PartnerClient partnerClient, OrderClient orderClient) {
        this.repo = repo;
        this.partnerClient = partnerClient;
        this.orderClient = orderClient;
    }

    public Invoice create(Invoice invoice) {
        // REST calls to partner-service and order-service — models real inter-service communication overhead
        partnerClient.getPartner(invoice.getPartnerId());
        orderClient.getOrder(invoice.getOrderId());
        if (invoice.getInvoiceNumber() == null) {
            invoice.setInvoiceNumber("INV-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
        }
        return repo.save(invoice);
    }

    @Transactional(readOnly = true)
    public List<Invoice> findAll() {
        return repo.findAll();
    }

    @Transactional(readOnly = true)
    public Invoice findById(Long id) {
        return repo.findById(id).orElseThrow(() ->
                new RuntimeException("Invoice not found: " + id));
    }

    @Transactional(readOnly = true)
    public List<Invoice> findByPartnerId(Long partnerId) {
        return repo.findByPartnerId(partnerId);
    }

    public Invoice updateStatus(Long id, Invoice.InvoiceStatus status) {
        Invoice invoice = findById(id);
        invoice.setStatus(status);
        return repo.save(invoice);
    }

    public void delete(Long id) {
        repo.deleteById(id);
    }
}
