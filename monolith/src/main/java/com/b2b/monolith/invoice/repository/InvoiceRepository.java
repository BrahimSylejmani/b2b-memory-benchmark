package com.b2b.monolith.invoice.repository;

import com.b2b.monolith.invoice.entity.Invoice;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface InvoiceRepository extends JpaRepository<Invoice, Long> {
    List<Invoice> findByPartnerId(Long partnerId);
    List<Invoice> findByOrderId(Long orderId);
}
