package com.b2b.monolith.invoice.service;

import com.b2b.monolith.invoice.entity.Invoice;
import com.b2b.monolith.invoice.repository.InvoiceRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Service
@Transactional
public class InvoiceService {

    private final InvoiceRepository repo;

    public InvoiceService(InvoiceRepository repo) {
        this.repo = repo;
    }

    public Invoice create(Invoice invoice) {
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
